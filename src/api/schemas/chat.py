"""Chat API Pydantic schemas — T9 REST + SSE models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    agent_type: str
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Response model for a single conversation."""

    id: str  # UUID as string
    user_id: str
    agent_type: str
    title: Optional[str]
    created_at: str  # ISO-8601
    updated_at: str  # ISO-8601


class MessageResponse(BaseModel):
    """Response model for a single chat message."""

    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: str


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""

    conversations: list[ConversationResponse]


class MessageHistoryResponse(BaseModel):
    """Response model for message history of a conversation."""

    messages: list[MessageResponse]
    conversation_id: str


class ChatStreamRequest(BaseModel):
    """Request body for the streaming chat endpoint."""

    message: str
    conversation_id: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    """Request body for updating a conversation (e.g. rename)."""

    title: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def conversation_to_response(conv: Any) -> ConversationResponse:
    """Convert a SQLAlchemy Conversation instance to a ConversationResponse."""
    return ConversationResponse(
        id=str(conv.id),
        user_id=conv.user_id,
        agent_type=conv.agent_type,
        title=conv.title,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
    )


def message_to_response(msg: Any) -> MessageResponse:
    """Convert a SQLAlchemy ChatMessage instance to a MessageResponse."""
    return MessageResponse(
        id=str(msg.id),
        conversation_id=str(msg.conversation_id),
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
    )
