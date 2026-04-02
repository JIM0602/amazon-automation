"""Agent API Pydantic schemas — T4/T5 REST API models."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AgentType(str, Enum):
    """Supported agent types."""

    selection = "selection"
    listing = "listing"
    competitor = "competitor"
    persona = "persona"
    ad_monitor = "ad_monitor"


class AgentRunRequest(BaseModel):
    """Request body for triggering an agent run."""

    dry_run: bool = True
    params: Optional[dict] = None  # agent-specific params e.g. category, asin


class AgentRunResponse(BaseModel):
    """Immediate response returned when an agent run is accepted (HTTP 202)."""

    run_id: str
    agent_type: str
    status: str = "running"
    message: str


class AgentRunStatus(BaseModel):
    """Detailed status of a single agent run."""

    run_id: str
    agent_type: str
    status: str  # running / success / failed
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    cost_usd: Optional[float] = None
    started_at: str  # ISO-8601
    finished_at: Optional[str] = None


class AgentRunList(BaseModel):
    """Paginated list of agent runs."""

    runs: list[AgentRunStatus]
    total: int
