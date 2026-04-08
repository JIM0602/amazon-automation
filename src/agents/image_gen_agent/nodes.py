"""Image Generation Agent nodes."""
from __future__ import annotations

import importlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    openai = importlib.import_module("openai")
    openai_available = True
except ImportError:
    openai = None
    openai_available = False

try:
    from src.db.connection import get_session_local
    from src.db.models import AgentRun
    db_available = True
except ImportError:
    get_session_local = None
    AgentRun = None
    db_available = False

try:
    from src.llm.client import chat
    llm_available = True
except ImportError:
    chat = None
    llm_available = False

from .schemas import ImageGenState


_SUPPORTED_STYLES = {"professional", "lifestyle", "minimal", "artistic"}


def _as_str(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def init_run(state: ImageGenState) -> ImageGenState:
    if state.get("error"):
        return state

    prompt = _as_str(state.get("prompt")).strip()
    product_name = _as_str(state.get("product_name")).strip() or None
    style = _as_str(state.get("style") or "professional").strip().lower()
    dry_run = state.get("dry_run", True)

    logger.info(
        "image_gen_agent init_run | dry_run=%s style=%s product_name=%s",
        dry_run,
        style,
        product_name,
    )

    if not prompt:
        state["error"] = "prompt is required"
        state["status"] = "failed"
        return state

    if style not in _SUPPORTED_STYLES:
        logger.warning("image_gen_agent init_run | unsupported style=%s, fallback to professional", style)
        style = "professional"

    state["prompt"] = prompt
    state["product_name"] = product_name
    state["style"] = style
    state["status"] = "running"

    run_id = str(uuid.uuid4())
    state["agent_run_id"] = run_id
    logger.info("image_gen_agent init_run | agent_run_id=%s", run_id)
    return state


def generate_prompt(state: ImageGenState) -> ImageGenState:
    if state.get("error"):
        return state

    prompt = _as_str(state.get("prompt", ""))
    product_name = _as_str(state.get("product_name", "")) or None
    style = _as_str(state.get("style", "professional"))
    dry_run = state.get("dry_run", True)

    logger.info("image_gen_agent generate_prompt | dry_run=%s", dry_run)

    if dry_run:
        enhanced_prompt = (
            f"[DRY RUN] Professional Amazon product marketing image for {product_name or 'the product'}: "
            f"{prompt}. Use clean studio lighting, a polished commercial composition, "
            f"clear focus on the product, and a {style} visual style."
        )
        state["enhanced_prompt"] = enhanced_prompt
        return state

    if not llm_available or chat is None:
        state["error"] = "LLM client is unavailable"
        state["status"] = "failed"
        return state

    system_message = (
        "You are an expert product photographer. Enhance this image description into a detailed DALL-E 3 prompt "
        "for Amazon product marketing. Include lighting, angle, background, and style details. Keep it under 200 words."
    )
    user_message = (
        f"Product name: {product_name or ''}\n"
        f"Style: {style}\n"
        f"Image description: {prompt}"
    )

    try:
        response = chat(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.6,
            max_tokens=350,
        )
        enhanced_prompt = str(response.get("content", "")).strip()
        if not enhanced_prompt:
            raise ValueError("empty prompt returned from LLM")
        state["enhanced_prompt"] = enhanced_prompt
        return state
    except Exception as exc:
        logger.error("image_gen_agent generate_prompt failed: %s", exc)
        state["error"] = f"generate_prompt failed: {exc}"
        state["status"] = "failed"
        return state


def generate_image(state: ImageGenState) -> ImageGenState:
    if state.get("error"):
        return state

    dry_run = state.get("dry_run", True)
    enhanced_prompt = _as_str(state.get("enhanced_prompt") or state.get("prompt") or "").strip()

    logger.info("image_gen_agent generate_image | dry_run=%s", dry_run)

    if dry_run:
        state["image_url"] = "https://mock-dalle.example.com/image.png"
        state["revised_prompt"] = "Mock revised prompt for testing"
        state["image_data"] = ""
        return state

    if not openai_available or openai is None:
        state["error"] = "openai library is unavailable"
        state["status"] = "failed"
        return state

    try:
        config_module = importlib.import_module("src.config")
        settings_loader = getattr(config_module, "get_settings", None)
        settings = settings_loader() if callable(settings_loader) else getattr(config_module, "settings")
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        client = openai.OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size=state.get("size", "1024x1024"),
            quality="standard",
            n=1,
        )

        data_item = response.data[0]
        state["image_url"] = getattr(data_item, "url", "") or ""
        state["revised_prompt"] = getattr(data_item, "revised_prompt", "") or ""
        state["image_data"] = getattr(data_item, "b64_json", "") or ""
        return state
    except Exception as exc:
        logger.error("image_gen_agent generate_image failed: %s", exc)
        state["error"] = f"generate_image failed: {exc}"
        state["status"] = "failed"
        return state


def save_results(state: ImageGenState) -> ImageGenState:
    if state.get("error"):
        return state

    dry_run = state.get("dry_run", True)
    agent_run_id = state.get("agent_run_id", "")

    logger.info("image_gen_agent save_results | dry_run=%s", dry_run)

    if dry_run:
        logger.info("image_gen_agent save_results | dry_run=True, skip DB write")
        return state

    if not db_available or get_session_local is None or AgentRun is None:
        logger.warning("image_gen_agent save_results | DB unavailable, skip persistence")
        return state

    try:
        run_uuid = uuid.UUID(_as_str(agent_run_id)) if agent_run_id else uuid.uuid4()
        result_json = {
            "prompt": state.get("prompt", ""),
            "product_name": state.get("product_name"),
            "style": state.get("style", "professional"),
            "size": state.get("size", "1024x1024"),
            "enhanced_prompt": state.get("enhanced_prompt", ""),
            "image_url": state.get("image_url", ""),
            "image_data": state.get("image_data", ""),
            "revised_prompt": state.get("revised_prompt", ""),
            "status": state.get("status", "running"),
            "error": state.get("error"),
        }

        SessionLocal = get_session_local()
        with SessionLocal() as session:
            run = session.get(AgentRun, run_uuid)
            if run is None:
                run = AgentRun(
                    id=run_uuid,
                    agent_type="image_gen_agent",
                    status="running",
                    input_summary=json.dumps({
                        "prompt": state.get("prompt", ""),
                        "product_name": state.get("product_name"),
                        "style": state.get("style", "professional"),
                        "size": state.get("size", "1024x1024"),
                    }),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
            setattr(run, "result_json", result_json)
            session.commit()

        logger.info("image_gen_agent save_results | persisted agent_run_id=%s", str(run_uuid))
        state["agent_run_id"] = str(run_uuid)
        return state
    except Exception as exc:
        logger.warning("image_gen_agent save_results DB write failed: %s", exc)
        return state


def finalize_run(state: ImageGenState) -> ImageGenState:
    if state.get("error") and state.get("status") != "failed":
        state["status"] = "failed"

    agent_run_id = state.get("agent_run_id", "")
    dry_run = state.get("dry_run", True)
    final_status = "failed" if state.get("error") else "completed"
    state["status"] = final_status

    logger.info(
        "image_gen_agent finalize_run | agent_run_id=%s status=%s",
        agent_run_id,
        final_status,
    )

    if dry_run:
        return state

    if not db_available or get_session_local is None or AgentRun is None or not agent_run_id:
        return state

    try:
        run_uuid = uuid.UUID(_as_str(agent_run_id))
        SessionLocal = get_session_local()
        with SessionLocal() as session:
            run = session.get(AgentRun, run_uuid)
            if run is not None:
                setattr(run, "status", final_status)
                setattr(run, "finished_at", datetime.now(timezone.utc))
                setattr(run, "output_summary", json.dumps(
                    {
                        "image_url": state.get("image_url", ""),
                        "revised_prompt": state.get("revised_prompt", ""),
                        "status": final_status,
                        "error": state.get("error"),
                    }
                )[:200])
                setattr(run, "result_json", {
                    "prompt": state.get("prompt", ""),
                    "product_name": state.get("product_name"),
                    "style": state.get("style", "professional"),
                    "size": state.get("size", "1024x1024"),
                    "enhanced_prompt": state.get("enhanced_prompt", ""),
                    "image_url": state.get("image_url", ""),
                    "image_data": state.get("image_data", ""),
                    "revised_prompt": state.get("revised_prompt", ""),
                    "status": final_status,
                    "error": state.get("error"),
                })
                session.commit()
        return state
    except Exception as exc:
        logger.warning("image_gen_agent finalize_run DB update failed: %s", exc)
        return state
