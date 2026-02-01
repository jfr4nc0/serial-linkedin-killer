"""
Interface definitions for LinkedIn MCP components.
Following SOLID principles to enable dependency inversion.
"""

from src.linkedin_mcp.interfaces.agents import IJobApplicationAgent
from src.linkedin_mcp.interfaces.services import (
    IBrowserManager,
    IJobApplicationService,
    IJobSearchService,
)

__all__ = [
    "IJobApplicationAgent",
    "IBrowserManager",
    "IJobApplicationService",
    "IJobSearchService",
]
