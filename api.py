"""FastAPI application wrapping TollNet's TollGate for AI agent compute-toll gateway services, featuring local database file persistence and dynamic YaCY crawl hooks."""

import json
import os
from typing import Any, Dict, Optional
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from tollnet.ledger import Ledger
from tollnet.model_provider import GeminiProvider
from tollnet.search_backend import YaCYBackend
from tollnet.toll_gate import TollGate

app = FastAPI(
    title="TollNet API",
    description="Compute-toll gateway for AI agents seeking web search access with automated audit trails and crawl fallback.",
    version="0.2.0",
)

# Initialize core singletons coordinating with internal ledger and orchestration modules
ledger = Ledger()
search_backend = YaCYBackend()
model_provider = GeminiProvider()
toll_gate = TollGate(
    search_backend=search_backend,
    model_provider=model_provider,
    ledger=ledger,
)


class SearchRequest(BaseModel):
    """Request model for agent web search."""

    agent_id: str = Field(..., description="Unique identifier of the AI agent.")
    query: str = Field(..., description="Search query string.")
    toll_cost: Optional[float] = Field(
        1.0, description="Cost in credits for the search."
    )


class TaskData(BaseModel):
    """Task data payload schema for work units."""

    cause: Optional[str] = Field(None, description="Research cause.")
    abstract: Optional[str] = Field(None, description="Scientific abstract text.")
    question: Optional[str] = Field(None, description="Task question.")
    expected_answer: Optional[str] = Field(None, description="Expected answer.")


class WorkSubmission(BaseModel):
    """Request model for submitting proof-of-work answers."""

    agent_id: str = Field(..., description="Unique identifier of the AI agent.")
    task: Dict[str, Any] = Field(..., description="Assigned work unit task dictionary.")
    answer: str = Field(..., description="Submitted answer to the work unit.")
    reward_amount: Optional[float] = Field(
        1.5, description="Credit reward upon successful verification."
    )


# Alias for backward compatibility
SubmitWorkRequest = WorkSubmission


def save_audit_to_json(
    audit_entry: Dict[str, Any], filename: str = "audit_trail.json"
) -> None:
    """Save an audit log entry by appending it cleanly to a local JSON array file.

    Args:
        audit_entry (Dict[str, Any]): The computation log / audit entry to save.
        filename (str): The target JSON filename. Defaults to "audit_trail.json".
    """
    try:
        data = []
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                try:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        if not isinstance(data, list):
                            data = [data]
                except json.JSONDecodeError:
                    data = []

        data.append(audit_entry)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


@app.post("/search", summary="Request web search (subject to compute toll)")
def search_endpoint(req: SearchRequest) -> Dict[str, Any]:
    """Execute a search request through TollGate. Checks ledger, deducts toll_cost if sufficient, and serves search hits or task challenge.

    Args:
        req (SearchRequest): The search request payload.

    Returns:
        Dict[str, Any]: Search results or a work unit challenge if balance is insufficient.
    """
    response = toll_gate.request_search(
        agent_id=req.agent_id,
        query=req.query,
        toll_cost=req.toll_cost if req.toll_cost is not None else 1.0,
    )
    return response


@app.post(
    "/submit_work",
    summary="Submit completed work unit with step-by-step audit trail, YaCY fallback crawling, and JSON persistence",
)
async def submit_work_endpoint(req: WorkSubmission) -> Dict[str, Any]:
    """Submit a work unit solution, execute dynamic YaCY crawling fallbacks if needed, persist audit trail, and return metrics.

    Args:
        req (WorkSubmission): The work submission payload.

    Returns:
        Dict[str, Any]: Nested dictionary containing status, verification result, reward, balance, and agent_computation_log.
    """
    task_dict = req.task
    abstract_text = str(task_dict.get("abstract", ""))
    cause_text = str(task_dict.get("cause", ""))
    expected_answer = str(task_dict.get("expected_answer", ""))
    submitted_answer = str(req.answer)

    # 1. Dynamic keyword isolation from incoming payload
    lower_content = f"{cause_text} {abstract_text}".lower()
    if "melanoma" in lower_content:
        query_term = "melanoma"
    elif "oncology" in lower_content:
        query_term = "oncology"
    elif "gene expression" in lower_content:
        query_term = "gene expression"
    else:
        query_term = "gene expression"

    yacy_snippets = []
    crawl_triggered = False
    verification_steps = []

    # 2. Query local YaCY search cluster at http://localhost:8090/yacysearch.json
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            yacy_resp = await client.get(
                "http://localhost:8090/yacysearch.json",
                params={"search": query_term},
            )
            if yacy_resp.status_code == 200:
                data = yacy_resp.json()
                channels = []
                if isinstance(data, dict):
                    channels = data.get("channels", data.get("items", []))
                elif isinstance(data, list):
                    channels = data

                for item in channels:
                    if isinstance(item, dict):
                        snippet = item.get(
                            "description",
                            item.get("snippet", item.get("title", str(item))),
                        )
                        yacy_snippets.append(str(snippet))
                    else:
                        yacy_snippets.append(str(item))

            # 3. Dynamic YaCY Crawl Fallback if zero indexed results are returned
            if not yacy_snippets:
                yacy_user = os.getenv("YACY_ADMIN_USER")
                yacy_pass = os.getenv("YACY_ADMIN_PASS")

                if yacy_user and yacy_pass:
                    verification_steps.append(
                        f"YaCY search for '{query_term}' returned zero indexed results. Initiating dynamic background crawl of https://example.com."
                    )
                    crawl_triggered = True
                    try:
                        crawl_resp = await client.post(
                            "http://localhost:8090/yacy/crawler_p.html",
                            auth=(yacy_user, yacy_pass),
                            data={
                                "crawlingURL": "https://example.com",
                                "crawlingDepth": "1",
                                "crawlingMode": "isolated",
                                "crawlingDomination": "domain",
                                "startCrawl": "Start New Crawl",
                            },
                        )
                        if crawl_resp.status_code in (200, 302, 303):
                            yacy_snippets.append(
                                "Dynamic background crawl of https://example.com successfully triggered on YaCY admin servlet."
                            )
                        else:
                            yacy_snippets.append(
                                f"YaCY crawler servlet responded with status code {crawl_resp.status_code}."
                            )
                    except Exception as crawl_err:
                        yacy_snippets.append(
                            f"YaCY crawler fallback hook encountered connection error: {str(crawl_err)}"
                        )
                else:
                    yacy_snippets.append(
                        "Dynamic background crawl skipped: YACY_ADMIN_USER and YACY_ADMIN_PASS environment variables are not set."
                    )
                    verification_steps.append(
                        "YaCY search returned zero hits, but automated background crawl was skipped because YACY_ADMIN_USER and YACY_ADMIN_PASS are not configured."
                    )
            else:
                verification_steps.append(
                    f"YaCY search successfully indexed {len(yacy_snippets)} result(s) for query term '{query_term}'."
                )
    except (httpx.RequestError, Exception) as net_err:
        yacy_snippets = [
            f"YaCY local search node offline (http://localhost:8090) due to network error: {str(net_err)}. Simulated fallback audit snippet used."
        ]
        verification_steps.append(
            "YaCY search cluster unreachable. Simulated offline fallback active."
        )

    # 4. Calculate whether the phrase "gene expression" is present inside the payload's abstract text using case-insensitive validation logic
    phrase_present = "gene expression" in abstract_text.lower()

    # 5. Build verification steps
    verification_steps.extend([
        f"Step 1: Isolated search keyword '{query_term}' from task payload context.",
        f"Step 2: Queried YaCY index resulting in {len(yacy_snippets)} audit snippet(s) (crawl triggered: {crawl_triggered}).",
        f"Step 3: Performed case-insensitive substring scan for phrase 'gene expression' in abstract text. Detected: {phrase_present}.",
        f"Step 4: Executed absolute truth assessment comparing model expected answer ('{expected_answer}') with agent submitted answer ('{submitted_answer}').",
    ])

    # 6. Evaluate verification and reward
    model_verified = model_provider.verify_work(req.agent_id, task_dict, req.answer)
    verified = model_verified and phrase_present

    reward_val = req.reward_amount if req.reward_amount is not None else 1.5
    if verified:
        new_balance = ledger.add_credits(req.agent_id, reward_val)
        status_val = "success"
        final_determination = (
            "Verification successful: agent correctly validated literature-mining task, "
            "satisfied proof-of-work criteria, and earned search credits."
        )
    else:
        reward_val = 0.0
        new_balance = ledger.get_balance(req.agent_id)
        status_val = "failure"
        final_determination = (
            "Verification failed: agent submitted answer did not match expected evaluation "
            "or phrase validation check failed."
        )

    # Clean up active task tracking if present
    if hasattr(toll_gate, "_active_tasks") and req.agent_id in toll_gate._active_tasks:
        del toll_gate._active_tasks[req.agent_id]

    # 7. Construct agent computation log
    agent_computation_log = {
        "query_term": query_term,
        "yacy_crawl_audit": yacy_snippets,
        "verification_steps": verification_steps,
        "final_determination": final_determination,
    }

    # 8. Save audit entry into local JSON array file 'audit_trail.json'
    save_audit_to_json(
        {
            "agent_id": req.agent_id,
            "status": status_val,
            "verified": verified,
            "reward": reward_val,
            "balance": new_balance,
            "computation_log": agent_computation_log,
        }
    )

    return {
        "status": status_val,
        "verified": verified,
        "reward": reward_val,
        "balance": new_balance,
        "agent_computation_log": agent_computation_log,
    }


@app.get("/balance/{agent_id}", summary="Get agent credit balance")
def get_balance_endpoint(agent_id: str) -> Dict[str, Any]:
    """Retrieve the current credit balance for an agent.

    Args:
        agent_id (str): The unique identifier of the agent.

    Returns:
        Dict[str, Any]: Agent ID and current credit balance.
    """
    balance = ledger.get_balance(agent_id)
    return {"agent_id": agent_id, "balance": balance}
