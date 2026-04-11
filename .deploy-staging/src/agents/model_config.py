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

# Agent type → preferred model/provider mapping
# Provider values are optional and kept backward compatible with plain strings.
AGENT_MODEL_MAP: dict[str, str | dict[str, str]] = {
    # Strong reasoning / data analysis
    "core_management": {"model": "gpt-4o", "provider": "openai"},
    "selection": {"model": "gpt-4o", "provider": "openai"},
    "competitor": {"model": "gpt-4o", "provider": "openai"},
    "persona": {"model": "gpt-4o", "provider": "openai"},
    "ad_monitor": {"model": "gpt-4o", "provider": "openai"},
    "image_generation": {"model": "gpt-4o", "provider": "openai"},
    "product_listing": {"model": "gpt-4o", "provider": "openai"},

    # Analytical writing / rule interpretation
    "brand_planning": {"model": "claude-3-5-sonnet-20241022", "provider": "anthropic"},
    "listing": {"model": "claude-3-5-sonnet-20241022", "provider": "anthropic"},
    "whitepaper": {"model": "claude-3-5-sonnet-20241022", "provider": "anthropic"},
    "auditor": {"model": "claude-3-5-sonnet-20241022", "provider": "anthropic"},

    # Cost-efficient for high-volume tasks
    "keyword_library": {"model": "gpt-4o-mini", "provider": "openai"},
    "inventory": {"model": "gpt-4o-mini", "provider": "openai"},
}


def _normalize_agent_model_config(value: str | dict[str, str]) -> dict[str, str]:
    if isinstance(value, str):
        return {"model": value, "provider": "openai"}
    model = value.get("model", DEFAULT_MODEL)
    provider = value.get("provider", "openai")
    return {"model": model, "provider": provider}


def get_agent_model_config(agent_type: str) -> dict[str, str]:
    """Get the normalized model/provider config for an agent type."""
    env_key = f"AGENT_MODEL_{agent_type.upper()}"
    env_model = os.environ.get(env_key)
    if env_model:
        logger.info("Using env override for %s: %s", agent_type, env_model)
        return {"model": env_model, "provider": "openai"}

    return _normalize_agent_model_config(AGENT_MODEL_MAP.get(agent_type, DEFAULT_MODEL))


def get_model_for_agent(agent_type: str) -> str:
    """Get the configured model for an agent type.

    Priority:
    1. Environment variable AGENT_MODEL_{AGENT_TYPE} (uppercase, hyphens→underscores)
    2. AGENT_MODEL_MAP entry
    3. DEFAULT_MODEL fallback
    """
    model_config = get_agent_model_config(agent_type)
    provider = model_config.get("provider", "openai")
    model = model_config.get("model", DEFAULT_MODEL)

    if provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        logger.info("OpenRouter key missing for %s; falling back to direct OpenAI route", agent_type)
        return model

    if provider == "anthropic":
        return model

    return model
