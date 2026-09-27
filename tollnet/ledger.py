"""Ledger implementation for tracking agent credit balances in memory."""

from typing import Dict


class Ledger:
    """In-memory ledger tracking credit balances for AI agents."""

    def __init__(self) -> None:
        """Initialize the Ledger with an empty balance dictionary."""
        self._balances: Dict[str, float] = {}

    def get_balance(self, agent_id: str) -> float:
        """Get the current credit balance for an agent.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            float: The credit balance (defaults to 0.0 if agent is not registered).
        """
        return self._balances.get(agent_id, 0.0)

    def add_credits(self, agent_id: str, amount: float) -> float:
        """Add credits to an agent's balance.

        Args:
            agent_id (str): The unique identifier of the agent.
            amount (float): The amount of credits to add.

        Returns:
            float: The new balance of the agent.
        """
        current = self.get_balance(agent_id)
        new_balance = current + amount
        self._balances[agent_id] = new_balance
        return new_balance

    def spend_credits(self, agent_id: str, amount: float) -> bool:
        """Attempt to deduct credits from an agent's balance.

        Args:
            agent_id (str): The unique identifier of the agent.
            amount (float): The amount of credits to spend.

        Returns:
            bool: True if sufficient credits were available and deducted, False otherwise.
        """
        current = self.get_balance(agent_id)
        if current >= amount:
            self._balances[agent_id] = current - amount
            return True
        return False
