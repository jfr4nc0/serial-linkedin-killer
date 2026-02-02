"""Shared Kafka message schemas between core and MCP."""

from pydantic import BaseModel


class MCPSearchComplete(BaseModel):
    batch_id: str
    status: str  # "completed" or "failed"
    total_employees: int
    companies_processed: int
    error: str | None = None
    trace_id: str = ""
