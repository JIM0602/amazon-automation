from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

try:
    from loguru import logger  # pyright: ignore[reportMissingImports]
except ImportError:
    import logging as _logging

    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

from src.config import settings
from src.db.models import KBReviewQueue
from src.llm.client import chat


class KBIterator:
    """Evaluate chat sessions and propose knowledge-base entries."""

    def __init__(self) -> None:
        self.enabled = bool(getattr(settings, "KB_SELF_ITERATION_ENABLED", True))
        self.max_messages = int(getattr(settings, "KB_SELF_ITERATION_MAX_MESSAGES", 60))
        self.max_chars = int(getattr(settings, "KB_SELF_ITERATION_MAX_CHARS", 12000))

    async def evaluate_and_propose(
        self,
        agent_type: str,
        conversation_messages: list[dict[str, str]],
        db: Session,
    ) -> bool:
        if not self.enabled:
            return False

        messages = self._trim_messages(conversation_messages)
        if not messages:
            return False

        signature = self._conversation_signature(agent_type, messages)
        if self._already_proposed(db, agent_type, signature):
            return False

        prompt = self._build_prompt(messages)
        response = await asyncio.to_thread(
            chat,
            model="gpt-4o-mini",
            messages=prompt,
            temperature=0.2,
            max_tokens=900,
        )

        content = str(response.get("content", "")).strip()
        if not content:
            return False

        parsed = self._parse_response(content)
        if parsed is None:
            return False

        if not bool(parsed.get("should_propose")):
            return False

        summary = str(parsed.get("summary", "")).strip()
        proposed_content = str(parsed.get("content", "")).strip()
        reasoning = str(parsed.get("reasoning", "")).strip()

        if not summary or not proposed_content:
            return False

        final_content = proposed_content
        if reasoning:
            final_content = f"{proposed_content}\n\nReasoning:\n{reasoning}"

        if self._already_proposed(db, agent_type, signature, summary=summary):
            return False

        entry = KBReviewQueue(
            content=final_content,
            source=f"agent_self_iteration:{agent_type}:{signature}",
            agent_type=agent_type,
            summary=summary,
            status="pending",
        )
        db.add(entry)
        db.commit()
        logger.info(f"KB self-iteration proposal created for agent_type={agent_type}")
        return True

    def _trim_messages(self, conversation_messages: list[dict[str, str]]) -> list[dict[str, str]]:
        trimmed: list[dict[str, str]] = []
        total_chars = 0
        for message in conversation_messages[-self.max_messages :]:
            role = str(message.get("role", ""))
            content = str(message.get("content", ""))
            if not role or not content:
                continue
            total_chars += len(content)
            if total_chars > self.max_chars:
                break
            trimmed.append({"role": role, "content": content})
        return trimmed

    def _build_prompt(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        system_prompt = (
            "You are a knowledge-base curator. Analyze this conversation. Did the agent discover any "
            "insights worth adding to our knowledge base? Consider market trends, successful strategies, "
            "error patterns, and new insights about products or categories. If yes, return a JSON object "
            "with keys: should_propose (boolean), summary (1 line), content (detailed KB entry), reasoning. "
            "If not, return should_propose false and keep the other fields short. Output JSON only."
        )
        return [{"role": "system", "content": system_prompt}, *messages]

    def _parse_response(self, content: str) -> dict[str, Any] | None:
        candidates = [content]
        if "```" in content:
            parts = content.split("```")
            for index, part in enumerate(parts):
                if index % 2 == 1:
                    candidates.append(part.strip().removeprefix("json").strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _conversation_signature(self, agent_type: str, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"agent_type": agent_type, "messages": messages}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _already_proposed(
        self,
        db: Session,
        agent_type: str,
        signature: str,
        summary: str | None = None,
    ) -> bool:
        existing = (
            db.query(KBReviewQueue)
            .filter(KBReviewQueue.source == f"agent_self_iteration:{agent_type}:{signature}")
            .first()
        )
        if existing is not None:
            return True

        return False
