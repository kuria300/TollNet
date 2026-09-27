"""Search backend definitions for TollNet, including abstract interface and YaCY implementation."""

from abc import ABC, abstractmethod
from typing import Any, List
import requests


class SearchBackend(ABC):
    """Abstract base class representing a search backend provider."""

    @abstractmethod
    def search(self, query: str) -> List[Any]:
        """Perform a search query and return a list of results.

        Args:
            query (str): The search query string.

        Returns:
            List[Any]: A list of search results.
        """
        pass


class YaCYBackend(SearchBackend):
    """Concrete search backend querying a local YaCY peer server with fallback."""

    def __init__(self, base_url: str = "http://localhost:8090") -> None:
        """Initialize the YaCY search backend.

        Args:
            base_url (str): The base URL of the local YaCY server.
        """
        self.base_url: str = base_url

    def search(self, query: str) -> List[Any]:
        """Search via YaCY API, falling back to mock results if unreachable.

        Args:
            query (str): The search query string.

        Returns:
            List[Any]: Search results from YaCY or mock results.
        """
        try:
            # YaCY typical JSON search endpoint or search page query
            endpoint = f"{self.base_url}/yacy/search.json"
            response = requests.get(
                endpoint, params={"search": query}, timeout=3.0
            )
            if response.status_code == 200:
                data = response.json()
                # Assuming YaCY returns a list or dict containing items
                if isinstance(data, dict) and "channels" in data:
                    return data.get("channels", [])
                if isinstance(data, list):
                    return data
                return [data]
        except (requests.RequestException, ValueError):
            pass

        # Graceful fallback to mock results when YaCY is unreachable
        return [
            {
                "title": f"Mock YaCY Result for: {query}",
                "url": "http://localhost:8090/mock/result",
                "snippet": f"Fallback search result for query '{query}' due to unreachable YaCY server.",
            }
        ]
