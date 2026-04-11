"""Chat REST + SSE endpoints for real-time agent conversations.

Provides 7 endpoints:
- POST   /api/chat/conversations                — create conversation
- GET    /api/chat/conversations                — list user's conversations
- GET    /api/chat/conversations/{id}           — get single conversation
- PUT    /api/chat/conversations/{id}           — update conversation (e.g. rename)
- GET    /api/chat/conversations/{id}/history   — get message history
- DELETE /api/chat/conversations/{id}           — delete conversation
- POST   /api/chat/{agent_type}/stream          — send message + stream SSE
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import require_role
from src.api.schemas.agents import AgentType
from src.api.schemas.chat import (
    ChatStreamRequest,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    MessageHistoryResponse,
    UpdateConversationRequest,
    conversation_to_response,
    message_to_response,
)
from src.api.sse import sse_response
from src.db import get_db
from src.db.models import Conversation
from src.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Valid agent types for chat: all AgentType enum values + "auditor"
_VALID_AGENT_TYPES = {e.value for e in AgentType} | {"auditor"}

# Boss-only agent types — operator cannot create or stream these
_BOSS_ONLY = {"auditor", "brand_planning"}


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_user_id(current_user: dict[str, Any]) -> str:
    """Extract user_id from the JWT user dict.

    The middleware maps JWT ``sub`` to ``username`` in request.state.user.
    """
    return str(current_user["username"])


def _check_boss_only(agent_type: str, current_user: dict[str, Any]) -> None:
    """Raise 403 if agent_type is boss-only and the user is not a boss."""
    if agent_type in _BOSS_ONLY and current_user.get("role") != "boss":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this agent type",
        )


def _validate_agent_type(agent_type: str) -> None:
    """Raise 404 if agent_type is not a recognised chat agent."""
    if agent_type not in _VALID_AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent type: {agent_type}",
        )


def _get_conversation_or_404(
    db: Session, conversation_id: str, user_id: str,
) -> Conversation:
    """Fetch a conversation by id, ensuring it belongs to the given user.

    Raises 404 if not found or not owned by the user.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid conversation_id format: {conversation_id}",
        ) from exc

    conv = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
    if conv is None or str(conv.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


# ---------------------------------------------------------------------------
#  POST /api/chat/conversations — create conversation
# ---------------------------------------------------------------------------

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    body: CreateConversationRequest,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Create a new chat conversation for the current user."""
    _validate_agent_type(body.agent_type)
    _check_boss_only(body.agent_type, current_user)

    user_id = _get_user_id(current_user)
    service = ChatService(db)
    try:
        conv = service.create_conversation(user_id, body.agent_type, body.title)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return conversation_to_response(conv)


# ---------------------------------------------------------------------------
#  GET /api/chat/conversations — list user's conversations
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    agent_type: Optional[str] = None,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """List all conversations belonging to the current user."""
    user_id = _get_user_id(current_user)
    service = ChatService(db)
    convs = service.list_conversations(user_id, agent_type)
    return ConversationListResponse(
        conversations=[conversation_to_response(c) for c in convs],
    )


# ---------------------------------------------------------------------------
#  GET /api/chat/{agent_type}/conversations — list conversations for agent
# ---------------------------------------------------------------------------

@router.get("/{agent_type}/conversations", response_model=list[ConversationResponse])
def list_agent_conversations(
    agent_type: str,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    """List conversations for a specific agent type.

    Returns an empty list when the user has no conversations for that agent.
    """
    _validate_agent_type(agent_type)
    _check_boss_only(agent_type, current_user)

    user_id = _get_user_id(current_user)
    service = ChatService(db)
    convs = service.list_conversations(user_id, agent_type)
    return [conversation_to_response(c) for c in convs]


# ---------------------------------------------------------------------------
#  GET /api/chat/conversations/{conversation_id} — get single conversation
# ---------------------------------------------------------------------------

@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: str,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Get a single conversation by id (must belong to current user)."""
    user_id = _get_user_id(current_user)
    conv = _get_conversation_or_404(db, conversation_id, user_id)
    return conversation_to_response(conv)


# ---------------------------------------------------------------------------
#  PUT /api/chat/conversations/{conversation_id} — update conversation
# ---------------------------------------------------------------------------

@router.put(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation(
    conversation_id: str,
    body: UpdateConversationRequest,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Update a conversation (e.g. rename). Must belong to current user."""
    user_id = _get_user_id(current_user)
    # Verify ownership first
    _get_conversation_or_404(db, conversation_id, user_id)

    from src.db.chat import update_conversation as db_update_conversation

    conv = db_update_conversation(db, uuid.UUID(conversation_id), title=body.title)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation_to_response(conv)


# ---------------------------------------------------------------------------
#  GET /api/chat/conversations/{conversation_id}/history — message history
# ---------------------------------------------------------------------------

@router.get(
    "/conversations/{conversation_id}/history",
    response_model=MessageHistoryResponse,
)
def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> MessageHistoryResponse:
    """Get message history for a conversation (must belong to current user)."""
    user_id = _get_user_id(current_user)

    # Verify ownership first
    _get_conversation_or_404(db, conversation_id, user_id)

    service = ChatService(db)
    try:
        messages = service.get_history(conversation_id, user_id, limit)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MessageHistoryResponse(
        conversation_id=conversation_id,
        messages=[message_to_response(m) for m in messages],
    )


# ---------------------------------------------------------------------------
#  GET /api/chat/{agent_type}/conversations/{conversation_id}/messages
# ---------------------------------------------------------------------------

@router.get("/{agent_type}/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    agent_type: str,
    conversation_id: str,
    limit: int = 50,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    """Get message history for a conversation under a specific agent type."""
    _validate_agent_type(agent_type)
    _check_boss_only(agent_type, current_user)

    user_id = _get_user_id(current_user)
    conv = _get_conversation_or_404(db, conversation_id, user_id)
    conv_agent_type = str(getattr(conv, "agent_type"))
    if conv_agent_type != agent_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    service = ChatService(db)
    try:
        messages = service.get_history(conversation_id, user_id, limit)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return [message_to_response(m) for m in messages]


# ---------------------------------------------------------------------------
#  DELETE /api/chat/conversations/{conversation_id} — delete conversation
# ---------------------------------------------------------------------------

@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Delete a conversation and its messages (must belong to current user)."""
    user_id = _get_user_id(current_user)
    service = ChatService(db)
    deleted = service.delete_conversation(conversation_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
#  POST /api/chat/{agent_type}/stream — send message + stream SSE response
# ---------------------------------------------------------------------------

@router.post("/{agent_type}/stream")
async def chat_stream_endpoint(
    agent_type: str,
    body: ChatStreamRequest,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
):
    """SSE streaming chat with an AI agent.

    Returns a ``text/event-stream`` response. Each chunk is an SSE frame
    containing a JSON payload with ``type`` and ``content`` fields.

    Path Parameters:
        agent_type: One of the supported :class:`AgentType` values or ``auditor``.

    Body:
        message: User message text.
        conversation_id: Optional existing conversation id to continue.
    """
    _validate_agent_type(agent_type)
    _check_boss_only(agent_type, current_user)

    user_id = _get_user_id(current_user)
    service = ChatService(db)

    # Auto-create conversation if not provided
    conversation_id = body.conversation_id
    if conversation_id is None:
        conv = service.create_conversation(user_id, agent_type)
        conversation_id = str(conv.id)

    # Stream response from ChatService
    generator = service.send_message(conversation_id, user_id, body.message)
    return await sse_response(generator, conversation_id=conversation_id)
