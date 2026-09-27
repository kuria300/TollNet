"""Unit tests for TollNet TollGate, Ledger, and mocked backends/providers."""

import unittest
from unittest.mock import MagicMock

from tollnet.ledger import Ledger
from tollnet.model_provider import GeminiProvider, ModelProvider
from tollnet.search_backend import SearchBackend
from tollnet.toll_gate import TollGate


class TestLedger(unittest.TestCase):
    """Test suite for Ledger credit tracking."""

    def setUp(self) -> None:
        """Set up a fresh ledger instance before each test."""
        self.ledger: Ledger = Ledger()

    def test_initial_balance_is_zero(self) -> None:
        """Verify new agent balance starts at 0.0."""
        self.assertEqual(self.ledger.get_balance("agent_1"), 0.0)

    def test_add_credits(self) -> None:
        """Verify adding credits correctly updates balance."""
        new_bal = self.ledger.add_credits("agent_1", 5.0)
        self.assertEqual(new_bal, 5.0)
        self.assertEqual(self.ledger.get_balance("agent_1"), 5.0)

    def test_spend_credits_success(self) -> None:
        """Verify spending credits when balance is sufficient."""
        self.ledger.add_credits("agent_1", 3.0)
        success = self.ledger.spend_credits("agent_1", 2.0)
        self.assertTrue(success)
        self.assertEqual(self.ledger.get_balance("agent_1"), 1.0)

    def test_spend_credits_insufficient(self) -> None:
        """Verify spending credits fails when balance is insufficient."""
        self.ledger.add_credits("agent_1", 1.0)
        success = self.ledger.spend_credits("agent_1", 2.0)
        self.assertFalse(success)
        self.assertEqual(self.ledger.get_balance("agent_1"), 1.0)


class TestGeminiProviderLiteratureTask(unittest.TestCase):
    """Test suite for GeminiProvider cancer research literature mining tasks."""

    def test_fallback_literature_task_structure(self) -> None:
        """Verify fallback task contains cancer research cause and correct expected answer."""
        provider = GeminiProvider(api_key="invalid_key")
        task = provider.assign_work_unit("agent_test")

        self.assertIn("cause", task)
        self.assertEqual(
            task["cause"],
            "Cancer research: literature mining for gene expression patterns",
        )
        self.assertIn("abstract", task)
        self.assertIn("expected_answer", task)
        self.assertEqual(task["expected_answer"], "Yes")

        # Verify work with correct yes/no answer
        self.assertTrue(provider.verify_work("agent_test", task, "Yes"))
        self.assertTrue(provider.verify_work("agent_test", task, "yes"))
        self.assertFalse(provider.verify_work("agent_test", task, "No"))


class TestTollGateWithMocks(unittest.TestCase):
    """Test suite for TollGate orchestration using MagicMocks."""

    def setUp(self) -> None:
        """Set up mocks and TollGate instance before each test."""
        self.mock_search = MagicMock(spec=SearchBackend)
        self.mock_model = MagicMock(spec=ModelProvider)
        self.ledger = Ledger()
        self.toll_gate = TollGate(
            search_backend=self.mock_search,
            model_provider=self.mock_model,
            ledger=self.ledger,
        )

    def test_request_search_with_sufficient_credits(self) -> None:
        """Test search request when agent has enough credits."""
        agent_id = "agent_rich"
        self.ledger.add_credits(agent_id, 2.0)
        self.mock_search.search.return_value = [{"title": "Python Programming"}]

        response = self.toll_gate.request_search(agent_id, "python", toll_cost=1.0)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["balance"], 1.0)
        self.assertEqual(response["results"], [{"title": "Python Programming"}])
        self.mock_search.search.assert_called_once_with("python")
        self.mock_model.assign_work_unit.assert_not_called()

    def test_request_search_with_insufficient_credits(self) -> None:
        """Test search request when agent lacks credits triggers work unit assignment."""
        agent_id = "agent_poor"
        # Balance is 0.0, toll is 1.0
        mock_task = {
            "cause": "Cancer research: literature mining for gene expression patterns",
            "abstract": "Test abstract.",
            "question": "Does this abstract mention 'gene expression'?",
            "expected_answer": "No",
        }
        self.mock_model.assign_work_unit.return_value = mock_task

        response = self.toll_gate.request_search(agent_id, "python", toll_cost=1.0)

        self.assertEqual(response["status"], "payment_required")
        self.assertEqual(response["task"], mock_task)
        self.assertEqual(response["balance"], 0.0)
        self.mock_model.assign_work_unit.assert_called_once_with(agent_id)
        self.mock_search.search.assert_not_called()

    def test_submit_work_success(self) -> None:
        """Test successful work submission rewards credits."""
        agent_id = "agent_poor"
        mock_task = {
            "cause": "Cancer research: literature mining for gene expression patterns",
            "abstract": "Test abstract.",
            "question": "Does this abstract mention 'gene expression'?",
            "expected_answer": "No",
        }
        self.mock_model.verify_work.return_value = True

        response = self.toll_gate.submit_work(
            agent_id, mock_task, "No", reward_amount=1.5
        )

        self.assertEqual(response["status"], "success")
        self.assertTrue(response["verified"])
        self.assertEqual(response["balance"], 1.5)
        self.mock_model.verify_work.assert_called_once_with(
            agent_id, mock_task, "No"
        )

    def test_submit_work_failure(self) -> None:
        """Test incorrect work submission grants no reward."""
        agent_id = "agent_poor"
        mock_task = {
            "cause": "Cancer research: literature mining for gene expression patterns",
            "abstract": "Test abstract.",
            "question": "Does this abstract mention 'gene expression'?",
            "expected_answer": "No",
        }
        self.mock_model.verify_work.return_value = False

        response = self.toll_gate.submit_work(
            agent_id, mock_task, "Yes", reward_amount=1.5
        )

        self.assertEqual(response["status"], "failure")
        self.assertFalse(response["verified"])
        self.assertEqual(response["balance"], 0.0)


if __name__ == "__main__":
    unittest.main()
