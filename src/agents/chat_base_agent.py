from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
import uuid
import logging

from sqlalchemy.orm import Session

from src.config import settings
from src.db.chat import create_conversation, add_message, get_conversation_history
from src.db.models import ChatMessage
from src.llm.client import chat_stream

logger = logging.getLogger(__name__)


class ChatBaseAgent(ABC):
    """Chat-capable abstract base for AI agents with streaming support."""

    def __init__(self, name: str):
        self.name: str = name
        self.dry_run: bool = settings.DRY_RUN

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def get_tools(self) -> list[object]:
        """Return available tools for this agent (empty list if none)."""
        ...

    @abstractmethod
    def get_model(self) -> str:
        """Return the preferred LLM model name for this agent."""
        ...

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier (e.g. 'core_management')."""
        ...

    def log(self, msg: str):
        logger.info(f"[{self.name}] {msg}")

    def warn(self, msg: str):
        logger.warning(f"[{self.name}] {msg}")

    async def chat(
        self,
        message: str,
        conversation_id: str | None,
        user_id: str,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        """Main chat entry point — streams response chunks."""
        conv_id: uuid.UUID
        if conversation_id is None:
            conversation = create_conversation(
                db,
                user_id,
                self.agent_type,
                title=message[:100],
            )
            conv_id = uuid.UUID(str(getattr(conversation, "id")))
        else:
            conv_id = uuid.UUID(str(conversation_id))

        history: list[ChatMessage] = get_conversation_history(db, conv_id, limit=50)
        messages: list[dict[str, str]] = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in history:
            messages.append({"role": str(msg.role), "content": str(msg.content)})
        messages.append({"role": "user", "content": message})

        _ = add_message(db, conv_id, role="user", content=message)

        full_response = ""
        async for chunk in chat_stream(
            messages,
            model=self.get_model(),
            agent_type=self.agent_type,
        ):
            full_response += chunk
            yield chunk

        _ = add_message(db, conv_id, role="assistant", content=full_response)
        yield f"\n\n[CONV_ID:{conv_id}]"

        # KB self-iteration hook — propose insights if any
        try:
            from src.knowledge_base.self_iteration import KBIterator

            iterator = KBIterator()
            await iterator.evaluate_and_propose(self.agent_type, messages, db)
        except Exception as e:
            self.warn(f"KB self-iteration failed (non-blocking): {e}")
