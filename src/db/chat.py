from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.db.models import Conversation, ChatMessage


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_conversation(db: Session, user_id: str, agent_type: str, title: str | None = None) -> Conversation:
    now = _utc_now_naive()
    conversation = Conversation(
        user_id=user_id,
        agent_type=agent_type,
        title=title,
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def add_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    metadata: dict[str, object] | None = None,
) -> ChatMessage:
    now = _utc_now_naive()
    last_created_at = cast(
        datetime | None,
        db.query(func.max(ChatMessage.created_at))
        .filter(ChatMessage.conversation_id == conversation_id)
        .scalar(),
    )
    if last_created_at is not None and now <= last_created_at:
        now = last_created_at + timedelta(microseconds=1)
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        metadata_json=metadata,
        created_at=now,
    )
    db.add(message)
    _ = db.query(Conversation).filter(Conversation.id == conversation_id).update(
        {Conversation.updated_at: now},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(message)
    return message


def get_conversation_history(db: Session, conversation_id: uuid.UUID, limit: int = 50) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .limit(limit)
        .all()
    )


def list_user_conversations(db: Session, user_id: str, agent_type: str | None = None) -> list[Conversation]:
    query = db.query(Conversation).filter(Conversation.user_id == user_id)
    if agent_type is not None:
        query = query.filter(Conversation.agent_type == agent_type)
    return (
        query.order_by(
            desc(func.coalesce(Conversation.updated_at, Conversation.created_at)),
            Conversation.created_at.desc(),
        )
        .all()
    )


def update_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    title: str | None = None,
) -> Conversation | None:
    """Update a conversation's mutable fields (currently only title).

    Returns the updated Conversation, or None if not found.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        return None
    conv_any = cast(Any, conv)
    if title is not None:
        conv_any.title = title
    conv_any.updated_at = _utc_now_naive()
    db.commit()
    db.refresh(conv)
    return conv
