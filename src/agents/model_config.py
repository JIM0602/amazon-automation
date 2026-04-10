"""Centralized model assignment for all chat agents.

Each agent type maps to a preferred LLM model. Agents can read their
assigned model via `get_model_for_agent(agent_type)`.

Model selection rationale:
- GPT-4o: Strong reasoning, data analysis, optimization math
- Claude-3.5-sonnet: Analytical writing, rule interpretation, structured reports
- GPT-4o-mini: High volume tasks, cost-efficient monitoring
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Default fallback model when no specific assignment exists
DEFAULT_MODEL = "gpt-4o-mini"

# Agent type → preferred model mapping
# Rationale documented per assignment
AGENT_MODEL_MAP: dict[str, str] = {
    # Strong reasoning / data analysis
    "core_management": "gpt-4o",
    "selection": "gpt-4o",
    "competitor": "gpt-4o",
    "persona": "gpt-4o",
    "ad_monitor": "gpt-4o",
    "image_generation": "gpt-4o",
    "product_listing": "gpt-4o",

    # Analytical writing / rule interpretation
    "brand_planning": "claude-3-5-sonnet-20241022",
    "listing": "claude-3-5-sonnet-20241022",
    "whitepaper": "claude-3-5-sonnet-20241022",
    "auditor": "claude-3-5-sonnet-20241022",

    # Cost-efficient for high-volume tasks
    "keyword_library": "gpt-4o-mini",
    "inventory": "gpt-4o-mini",
}


def get_model_for_agent(agent_type: str) -> str:
    """Get the configured model for an agent type.

    Priority:
    1. Environment variable AGENT_MODEL_{AGENT_TYPE} (uppercase, hyphens→underscores)
    2. AGENT_MODEL_MAP entry
    3. DEFAULT_MODEL fallback
    """
    # Check env override first
    env_key = f"AGENT_MODEL_{agent_type.upper()}"
    env_model = os.environ.get(env_key)
    if env_model:
        logger.info("Using env override for %s: %s", agent_type, env_model)
        return env_model

    model = AGENT_MODEL_MAP.get(agent_type, DEFAULT_MODEL)
    return model
