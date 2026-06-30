"""Python client and MCP server for Eight person-search workflows."""

from .client import EightClient
from .models import CardResult, CompanyResult, PersonDetail, SearchResult

__all__ = ["CardResult", "CompanyResult", "EightClient", "PersonDetail", "SearchResult"]
__version__ = "0.2.0"
