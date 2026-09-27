"""TollGate orchestrator for TollNet linking search backend, model provider, and ledger."""

from typing import Any, Dict, List, Optional
from tollnet.ledger import Ledger
from tollnet.model_provider import ModelProvider
from tollnet.search_backend import SearchBackend


class TollGate:
    """Orchestrates compute tolls, work unit challenges, credit ledger, and search access."""

    def __init__(
        self,
        search_backend: SearchBackend,
        model_provider: ModelProvider,
        ledger: Ledger,
    ) -> None:
        """Initialize the TollGate orchestrator.

        Args:
            search_backend (SearchBackend): The search backend instance.
            model_provider (ModelProvider): The model provider instance for work units.
            ledger (Ledger): The ledger tracking agent credit balances.
        """
        self.search_backend: SearchBackend = search_backend
        self.model_provider: ModelProvider = model_provider
        self.ledger: Ledger = ledger
        # Optionally track active assigned tasks per agent for verification context if needed
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    def request_search(
        self, agent_id: str, query: str, toll_cost: float = 1.0
    ) -> Dict[str, Any]:
        """Request a search. Deducts toll if agent has enough credits; otherwise returns a work unit.

        Args:
            agent_id (str): The unique identifier of the AI agent.
            query (str): The search query string.
            toll_cost (float): The credit cost for performing a search. Defaults to 1.0.

        Returns:
            Dict[str, Any]: Search results if authorized, or a work unit challenge if payment required.
        """
        if self.ledger.spend_credits(agent_id, toll_cost):
            results = self.search_backend.search(query)
            balance = self.ledger.get_balance(agent_id)
            return {
                "status": "success",
                "results": results,
                "balance": balance,
            }
        else:
            task = self.model_provider.assign_work_unit(agent_id)
            self._active_tasks[agent_id] = task
            balance = self.ledger.get_balance(agent_id)
            return {
                "status": "payment_required",
                "task": task,
                "balance": balance,
                "message": "Insufficient credits. Complete the assigned work unit to earn compute credits.",
            }

    def submit_work(
        self,
        agent_id: str,
        task: Dict[str, Any],
        answer: str,
        reward_amount: float = 1.5,
    ) -> Dict[str, Any]:
        """Submit an answer to a work unit challenge to earn credits.

        Args:
            agent_id (str): The unique identifier of the AI agent.
            task (Dict[str, Any]): The task/puzzle dictionary.
            answer (str): The solution answer submitted by the agent.
            reward_amount (float): The credit reward upon successful verification. Defaults to 1.5.

        Returns:
            Dict[str, Any]: Verification status and updated balance.
        """
        # Verify work using model provider
        is_valid = self.model_provider.verify_work(agent_id, task, answer)
        if is_valid:
            new_balance = self.ledger.add_credits(agent_id, reward_amount)
            if agent_id in self._active_tasks:
                del self._active_tasks[agent_id]
            return {
                "status": "success",
                "verified": True,
                "reward": reward_amount,
                "balance": new_balance,
            }
        else:
            balance = self.ledger.get_balance(agent_id)
            return {
                "status": "failure",
                "verified": False,
                "message": "Incorrect answer. Try again.",
                "balance": balance,
            }
