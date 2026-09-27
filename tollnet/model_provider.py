"""Model provider definitions for TollNet, including abstract interface and Gemini implementation."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ModelProvider(ABC):
    """Abstract base class representing an AI model provider for work unit generation and verification."""

    @abstractmethod
    def assign_work_unit(self, agent_id: str) -> Dict[str, Any]:
        """Assign a compute work unit (puzzle/task) to an agent.

        Args:
            agent_id (str): The unique identifier of the requesting agent.

        Returns:
            Dict[str, Any]: A dictionary describing the task/puzzle.
        """
        pass

    @abstractmethod
    def verify_work(
        self, agent_id: str, task: Dict[str, Any], submitted_answer: str
    ) -> bool:
        """Verify the agent's submitted answer for the given task.

        Args:
            agent_id (str): The unique identifier of the agent.
            task (Dict[str, Any]): The original task dictionary.
            submitted_answer (str): The answer submitted by the agent.

        Returns:
            bool: True if the answer is correct, False otherwise.
        """
        pass


class GeminiProvider(ModelProvider):
    """Concrete model provider using the google-genai SDK with local puzzle fallback."""

    def __init__(
        self,
        model_name: str = "gemini-3.8-flash",
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the Gemini model provider.

        Args:
            model_name (str): The model name to use. Defaults to "gemini-3.8-flash".
            api_key (Optional[str]): The Gemini API key. If not provided, read from GEMINI_API_KEY env var.
        """
        self.model_name: str = model_name
        self.api_key: Optional[str] = api_key or os.getenv("GEMINI_API_KEY")
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the google-genai client if API key is available."""
        if self.api_key and self.api_key != "your_key_here":
            try:
                from google import genai  # type: ignore

                self._client = genai.Client(api_key=self.api_key)
            except (ImportError, Exception):
                self._client = None

    def assign_work_unit(self, agent_id: str) -> Dict[str, Any]:
        """Assign a literature-mining work unit for cancer research.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            Dict[str, Any]: The assigned task dictionary including the cause, abstract, question, and expected answer.
        """
        cause = "Cancer research: literature mining for gene expression patterns"

        if self._client:
            try:
                prompt = (
                    "Generate a short, realistic-sounding 2 to 3 sentence fake scientific abstract about cancer or gene research. "
                    "Randomly decide whether or not to include the exact phrase 'gene expression' in the abstract. "
                    "Determine whether the phrase 'gene expression' appears in the abstract. "
                    "Provide your response in the following exact format:\n"
                    "ABSTRACT: [the 2-3 sentence abstract]\n"
                    "ANSWER: [Yes or No]"
                )
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                text = response.text
                if text:
                    abstract_text = ""
                    expected = "No"
                    for line in text.splitlines():
                        if line.startswith("ABSTRACT:"):
                            abstract_text = line.replace("ABSTRACT:", "").strip()
                        elif line.startswith("ANSWER:"):
                            expected = line.replace("ANSWER:", "").strip()

                    if not abstract_text:
                        abstract_text = text.strip()

                    return {
                        "type": "ai_generated_literature",
                        "cause": cause,
                        "abstract": abstract_text,
                        "question": "Does this abstract mention 'gene expression'? (Answer Yes or No)",
                        "expected_answer": expected if expected in ("Yes", "No") else "Yes",
                    }
            except Exception:
                pass

        # Fallback static literature puzzle
        return {
            "type": "static_literature_task",
            "cause": cause,
            "abstract": (
                "Recent studies in oncology demonstrate that therapeutic targeting of p53 pathways "
                "alters gene expression profiles in metastatic melanoma. Furthermore, synergistic inhibition "
                "of tyrosine kinases reduces tumor volume in murine models."
            ),
            "question": "Does this abstract mention 'gene expression'? (Answer Yes or No)",
            "expected_answer": "Yes",
        }

    def verify_work(
        self, agent_id: str, task: Dict[str, Any], submitted_answer: str
    ) -> bool:
        """Verify the submitted yes/no answer against what Gemini determined is correct for that abstract.

        Args:
            agent_id (str): The unique identifier of the agent.
            task (Dict[str, Any]): The task dictionary containing expected_answer.
            submitted_answer (str): The answer provided by the agent.

        Returns:
            bool: True if verification succeeds, False otherwise.
        """
        expected = str(task.get("expected_answer", "")).strip()
        cleaned_answer = str(submitted_answer).strip()
        return cleaned_answer.lower() == expected.lower()
