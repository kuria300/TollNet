# TollNet: AI Agent SDK & Compute-Toll Gateway

TollNet is an advanced compute-toll gateway system for AI agents that want to search the web. Instead of paying fiat money or API subscription fees, an AI agent must complete a small compute "work unit" (proof-of-work/literature mining puzzle generated or verified by Gemini) before it is authorized to perform web searches.

---

## The "Compute Instead of Fiat" Philosophy

Traditional AI agent web search gateways rely on paid subscription keys, credit cards, or centralized API microtransactions. TollNet reimagines agent economics around proof-of-useful-work:
- **Zero Financial Friction**: Autonomous agents do not require payment instruments.
- **Meaningful Productivity**: Instead of forcing agents to spend compute on arbitrary cryptographic hash collisions, TollNet channels their compute-toll work units toward real, incremental progress on scientific literature mining for cancer research—specifically tasking agents with identifying gene expression patterns across biomedical abstracts.

---

## System Architecture

- **`tollnet/client.py` (`TollNetClient`)**: The synchronous Python client SDK wrapper used by AI agents to interact with the gateway, handle balances, execute searches, and catch `WorkRequiredException`.
- **`tollnet/exceptions.py` (`WorkRequiredException`)**: Custom exception raised when an agent has insufficient search credits, carrying the assigned task payload.
- **`tollnet/search_backend.py` (`YaCYBackend`)**: Queries a local YaCY search cluster at `http://localhost:8090` with graceful fallback to mock results.
- **`tollnet/model_provider.py` (`GeminiProvider`)**: Uses the `google-genai` SDK to generate cancer literature mining abstracts and verify agent answers, with local puzzle fallbacks.
- **`tollnet/ledger.py` (`Ledger`)**: In-memory credit ledger tracking balances per `agent_id`.
- **`tollnet/toll_gate.py` (`TollGate`)**: Orchestrator coordinating credit deductions, search authorizations, and work assignments.
- **`api.py` (FastAPI Application)**: Exposes endpoints (`/search`, `/submit_work`, `/balance/{agent_id}`), coordinates ledger/orchestration modules, executes asynchronous YaCY crawling fallbacks, and persists logs.

---

## Local Database Ledger (`audit_trail.json`)

TollNet features a built-in local database ledger that automatically records every completed work submission and step-by-step computational verification trail. Each entry is appended cleanly into a local JSON array file named **`audit_trail.json`** inside the execution root directory, preserving all historical audit records.

### Live Troubleshooting & Monitoring Commands

Developers can inspect, monitor, and format audit records live from the terminal using standard utilities:

- **Monitor audit entries in real-time:**
  ```bash
  tail -f audit_trail.json
  ```
- **Pretty-print and inspect recorded audit trails:**
  ```bash
  python3 -m json.tool audit_trail.json
  ```

---

## Automated Fallback Architecture

TollNet incorporates intelligent automated fallback and harvesting hooks:
- **Dynamic Keyword Isolation**: Incoming task payloads are inspected to isolate target research keywords (e.g., `"gene expression"`, `"melanoma"`, or `"oncology"`).
- **Zero-Hit YaCY Crawl Fallback**: If querying the local YaCY search cluster at `http://localhost:8090/yacysearch.json` for the isolated keyword returns zero indexed results, the FastAPI gateway checks for `YACY_ADMIN_USER` and `YACY_ADMIN_PASS` environment variables.
- **Environment-Based Authentication**: If administrative credentials are set in the environment, TollNet asynchronously invokes YaCY's administrative crawler servlet (`http://localhost:8090/yacy/crawler_p.html`) using HTTP Basic Auth to trigger an isolated background crawl of `https://example.com` (`crawlingDepth: 1`, `crawlingMode: isolated`). If unset, the auto-crawl feature is skipped gracefully rather than attempting default credentials.

---

## Installation

1. Clone or open the repository.
2. Install the package in editable mode with dependencies:
   ```bash
   pip install -e .
   ```
   *(Or install via `pip install -r requirements.txt`)*

3. Configure environment variables (copy `.env.example` to `.env` and add your Gemini API key if desired):
   ```bash
   cp .env.example .env
   ```

---

## Running the API

Start the FastAPI development server using Uvicorn:
```bash
uvicorn api:app --reload
```

---

## Python SDK Usage Guide

The following example demonstrates how an AI agent initializes `TollNetClient`, attempts a search, catches a `WorkRequiredException` challenge, and solves it by calling `.submit_work()`:

```python
from tollnet import TollNetClient, WorkRequiredException

# Initialize the client SDK for an AI agent
client = TollNetClient(base_url="http://localhost:8000", agent_id="agent_alpha")

try:
    print(f"Checking balance for {client.agent_id}...")
    balance = client.get_balance()
    print(f"Current Balance: {balance} credits")

    # Attempt to perform a web search (costs 1.0 credit by default)
    results = client.search("cancer immunotherapy")
    print("Search successful! Results:", results)

except WorkRequiredException as e:
    print("\n[!] Insufficient credits. Compute work required!")
    print(f"Research Cause: {e.task.get('cause')}")
    print(f"Scientific Abstract:\n  {e.task.get('abstract')}")
    print(f"Challenge Question: {e.task.get('question')}")

    # Solve the literature mining challenge (e.g., answering whether 'gene expression' is mentioned)
    solution = "Yes"
    print(f"\nSubmitting solution: '{solution}'...")

    confirmation = client.submit_work(task=e.task, answer=solution)
    print("Work submission confirmed!")
    print(f"New Balance: {confirmation.get('balance')} credits")
    print(f"Reward Earned: {confirmation.get('reward')} credits")
    print("Computation Audit Log Summary:", confirmation.get("agent_computation_log", {}).get("final_determination"))
```

---

## Step-by-Step Testing Flow (cURL)

To test the `/submit_work` endpoint directly and inspect the step-by-step telemetry, run the following cleaned-up multi-line `curl` command targeting `http://127.0.0.1:8000/submit_work`:

```bash
curl -X POST http://127.0.0.1:8000/submit_work \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_alpha",
    "task": {
      "cause": "Cancer research: literature mining for gene expression patterns",
      "abstract": "Recent studies in oncology demonstrate that therapeutic targeting of p53 pathways alters gene expression profiles in metastatic melanoma.",
      "question": "Does this abstract mention \"gene expression\"? (Answer Yes or No)",
      "expected_answer": "Yes"
    },
    "answer": "Yes",
    "reward_amount": 1.5
  }'
```

### Sample Successful Response Telemetry

A successful submission returns a JSON payload containing credit tracking metrics and the complete `agent_computation_log` audit block:

```json
{
  "status": "success",
  "verified": true,
  "reward": 1.5,
  "balance": 1.5,
  "agent_computation_log": {
    "query_term": "gene expression",
    "yacy_crawl_audit": [
      "Simulated fallback audit snippet: Oncology study evaluating gene expression in tumor samples."
    ],
    "verification_steps": [
      "Step 1: Isolated search keyword 'gene expression' from task payload context.",
      "Step 2: Queried YaCY index resulting in 1 audit snippet(s) (crawl triggered: false).",
      "Step 3: Performed case-insensitive substring scan for phrase 'gene expression' in abstract text. Detected: True.",
      "Step 4: Executed absolute truth assessment comparing model expected answer ('Yes') with agent submitted answer ('Yes')."
    ],
    "final_determination": "Verification successful: agent correctly validated literature-mining task, satisfied proof-of-work criteria, and earned search credits."
  }
}
```

---

## Running Tests

Run the unit test suite using `unittest`:
```bash
python -m unittest discover tests
```
