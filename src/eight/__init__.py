"""Python client and MCP server for Eight person-search workflows."""

from .client import EightClient
from .models import CardResult, SearchResult

__all__ = ["CardResult", "EightClient", "SearchResult"]
__version__ = "0.1.2"
