from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from importlib import import_module
from typing import Protocol, cast

from sqlalchemy.orm import Session

from src.api.schemas.agents import AgentType
from src.agents.chat_base_agent import ChatBaseAgent
from src.db.chat import (
    create_conversation as db_create_conversation,
    get_conversation_history,
    list_user_conversations,
)
from src.db.models import ChatMessage, Conversation


_VALID_CHAT_AGENT_TYPES = {agent_type.value for agent_type in AgentType} | {"auditor", "keyword_library"}


class _ChatAgentFactory(Protocol):
    def __call__(self) -> ChatBaseAgent:
        ...


# Lazy import registry — maps agent_type string to (module_path, class_name)
# This avoids importing all agents at module load time.
AGENT_REGISTRY: dict[str, tuple[str, str]] = {
    "core_management": ("src.agents.core_agent.chat_agent", "CoreManagementChatAgent"),
    "brand_planning": ("src.agents.brand_planning_agent.chat_agent", "BrandPlanningChatAgent"),
    "selection": ("src.agents.selection_agent.chat_agent", "SelectionChatAgent"),
    "whitepaper": ("src.agents.whitepaper_agent.chat_agent", "WhitepaperChatAgent"),
    "competitor": ("src.agents.competitor_agent.chat_agent", "CompetitorChatAgent"),
    "persona": ("src.agents.persona_agent.chat_agent", "PersonaChatAgent"),
    "listing": ("src.agents.listing_agent.chat_agent", "ListingChatAgent"),
    "image_generation": ("src.agents.image_gen_agent.chat_agent", "ImageGenChatAgent"),
    "product_listing": ("src.agents.product_listing_agent.chat_agent", "ProductListingChatAgent"),
    "inventory": ("src.agents.inventory_agent.chat_agent", "InventoryChatAgent"),
    "ad_monitor": ("src.agents.ad_monitor_agent.chat_agent", "AdMonitorChatAgent"),
    "auditor": ("src.agents.auditor.chat_agent", "AuditorChatAgent"),
    "keyword_library": ("src.agents.keyword_library.chat_agent", "KeywordLibraryChatAgent"),
}


def get_chat_agent(agent_type: str) -> ChatBaseAgent:
    """Instantiate and return the ChatBaseAgent for the given agent_type."""
    try:
        module_path, class_name = AGENT_REGISTRY[agent_type]
    except KeyError as exc:
        raise ValueError(f"Chat agent not registered: {agent_type!r}") from exc

    module = import_module(module_path)
    agent_class = cast(_ChatAgentFactory, getattr(module, class_name))
    agent = agent_class()
    return agent


class ChatService:
    """Orchestration layer for agent conversations."""

    def __init__(self, db: Session):
        self.db: Session = db

    def create_conversation(self, user_id: str, agent_type: str, title: str | None = None) -> Conversation:
        """Create a new conversation. Validates agent_type exists."""
        if agent_type not in _VALID_CHAT_AGENT_TYPES:
            raise ValueError(f"Invalid agent_type: {agent_type!r}")
        return db_create_conversation(self.db, user_id=user_id, agent_type=agent_type, title=title)

    async def send_message(self, conversation_id: str, user_id: str, message: str) -> AsyncGenerator[str, None]:
        """Send message to agent and stream response."""
        conversation = self.db.query(Conversation).filter(Conversation.id == uuid.UUID(conversation_id)).first()
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id!r}")
        conversation_user_id = cast(str, getattr(conversation, "user_id"))
        if conversation_user_id != user_id:
            raise PermissionError("Conversation does not belong to the current user")

        conversation_uuid = cast(uuid.UUID, getattr(conversation, "id"))
        agent_type = cast(str, getattr(conversation, "agent_type"))
        agent = get_chat_agent(agent_type)
        async for chunk in agent.chat(message, str(conversation_uuid), user_id, self.db):
            yield chunk

    def get_history(self, conversation_id: str, user_id: str, limit: int = 50) -> list[ChatMessage]:
        """Get conversation message history. Validates user owns conversation."""
        conversation = self.db.query(Conversation).filter(Conversation.id == uuid.UUID(conversation_id)).first()
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id!r}")
        conversation_user_id = cast(str, getattr(conversation, "user_id"))
        if conversation_user_id != user_id:
            raise PermissionError("Conversation does not belong to the current user")
        conversation_uuid = cast(uuid.UUID, getattr(conversation, "id"))
        return get_conversation_history(self.db, conversation_uuid, limit=limit)

    def list_conversations(self, user_id: str, agent_type: str | None = None) -> list[Conversation]:
        """List user's conversations, optionally filtered by agent_type."""
        return list_user_conversations(self.db, user_id, agent_type=agent_type)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Soft delete a conversation. Returns True if found and deleted."""
        conversation = self.db.query(Conversation).filter(Conversation.id == uuid.UUID(conversation_id)).first()
        if conversation is None:
            return False

        conversation_user_id = cast(str, getattr(conversation, "user_id"))
        if conversation_user_id != user_id:
            return False

        conversation_uuid = cast(uuid.UUID, getattr(conversation, "id"))
        _ = self.db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_uuid).delete(
            synchronize_session=False
        )
        self.db.delete(conversation)
        self.db.commit()
        return True
