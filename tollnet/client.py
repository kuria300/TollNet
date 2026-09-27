"""Synchronous Python client SDK wrapper for TollNet AI Agent Compute-Toll Gateway."""

from typing import Any, Dict, Optional
import requests

from tollnet.exceptions import WorkRequiredException


class TollNetClient:
    """Client SDK for AI agents to interact with the TollNet compute-toll gateway."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        agent_id: str = "agent_default",
    ) -> None:
        """Initialize the TollNet client.

        Args:
            base_url (str): The base URL of the TollNet API gateway. Defaults to "http://localhost:8000".
            agent_id (str): The unique identifier of the AI agent. Defaults to "agent_default".
        """
        self.base_url: str = base_url.rstrip("/")
        self.agent_id: str = agent_id

    def get_balance(self) -> float:
        """Fetch the current credit balance of the agent from the gateway.

        Returns:
            float: The current credit balance.
        """
        url = f"{self.base_url}/balance/{self.agent_id}"
        response = requests.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return float(data.get("balance", 0.0))

    def search(self, query: str, toll_cost: float = 1.0) -> Dict[str, Any]:
        """Request a web search. If credits are insufficient, raises WorkRequiredException with the task challenge.

        Args:
            query (str): The search query string.
            toll_cost (float): The credit cost for the search. Defaults to 1.0.

        Returns:
            Dict[str, Any]: Search results and remaining balance if authorized.

        Raises:
            WorkRequiredException: If the agent lacks sufficient credits and must complete a work unit.
        """
        url = f"{self.base_url}/search"
        payload = {
            "agent_id": self.agent_id,
            "query": query,
            "toll_cost": toll_cost,
        }
        response = requests.post(url, json=payload, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "payment_required" or "task" in data:
            task = data.get("task", {})
            raise WorkRequiredException(task)

        return data

    def submit_work(
        self,
        task: Dict[str, Any],
        answer: str,
        reward_amount: float = 1.5,
    ) -> Dict[str, Any]:
        """Submit an answer to an assigned work unit to earn search credits.

        Args:
            task (Dict[str, Any]): The task/puzzle dictionary received from WorkRequiredException.
            answer (str): The solution answer.
            reward_amount (float): The credit reward upon successful verification. Defaults to 1.5.

        Returns:
            Dict[str, Any]: Verification confirmation dictionary containing status, reward, balance, and audit log.
        """
        url = f"{self.base_url}/submit_work"
        payload = {
            "agent_id": self.agent_id,
            "task": task,
            "answer": answer,
            "reward_amount": reward_amount,
        }
        response = requests.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json()
