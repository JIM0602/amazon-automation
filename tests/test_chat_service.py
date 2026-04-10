"""Tests for ChatService orchestration layer."""

from __future__ import annotations

import asyncio
from typing import Any, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import Base, ChatMessage, Conversation
from src.services import chat as chat_service_module
from src.services.chat import ChatService, get_chat_agent


class DummyChatAgent:
    def __init__(self, chunks: list[str] | None = None):
        self._chunks: list[str] = chunks or ["hello", " world"]

    async def chat(self, message: str, conversation_id: str | None, user_id: str, db: Any):  # noqa: ANN001
        for chunk in self._chunks:
            yield chunk


@pytest.fixture()
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sqlite_session(sqlite_engine):
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def monkeypatch_context(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    return monkeypatch


def test_create_conversation_valid_and_invalid_agent_type(sqlite_session):
    service = ChatService(sqlite_session)

    conversation = service.create_conversation("user-1", "selection", title="hello")
    conversation_id = str(getattr(conversation, "id"))
    conversation_user_id = str(getattr(conversation, "user_id"))
    conversation_agent_type = str(getattr(conversation, "agent_type"))
    conversation_title = getattr(conversation, "title")

    assert conversation_id
    assert conversation_user_id == "user-1"
    assert conversation_agent_type == "selection"
    assert conversation_title == "hello"

    with pytest.raises(ValueError):
        service.create_conversation("user-1", "not-a-real-agent")


def test_list_conversations_returns_correct_results(sqlite_session):
    service = ChatService(sqlite_session)

    first = service.create_conversation("user-1", "selection", title="first")
    second = service.create_conversation("user-1", "listing", title="second")
    other_user = service.create_conversation("user-2", "selection", title="other")

    conversations = service.list_conversations("user-1")
    filtered = service.list_conversations("user-1", agent_type="selection")

    assert [str(getattr(c, "id")) for c in conversations] == [str(second.id), str(first.id)]
    assert str(getattr(other_user, "id")) not in [str(getattr(c, "id")) for c in conversations]
    assert [str(getattr(c, "id")) for c in filtered] == [str(first.id)]


def test_get_history_validates_user_ownership(sqlite_session):
    service = ChatService(sqlite_session)
    conversation = service.create_conversation("user-1", "selection")

    message = ChatMessage(conversation_id=conversation.id, role="user", content="hi")
    sqlite_session.add(message)
    sqlite_session.commit()

    history = service.get_history(str(conversation.id), "user-1")

    assert [str(getattr(item, "id")) for item in history] == [str(message.id)]

    with pytest.raises(PermissionError):
        service.get_history(str(conversation.id), "user-2")


def test_delete_conversation_removes_records(sqlite_session):
    service = ChatService(sqlite_session)
    conversation = service.create_conversation("user-1", "selection")

    first = ChatMessage(conversation_id=conversation.id, role="user", content="hi")
    second = ChatMessage(conversation_id=conversation.id, role="assistant", content="there")
    sqlite_session.add_all([first, second])
    sqlite_session.commit()

    assert service.delete_conversation(str(conversation.id), "user-1") is True
    assert sqlite_session.query(Conversation).count() == 0
    assert sqlite_session.query(ChatMessage).count() == 0
    assert service.delete_conversation(str(conversation.id), "user-1") is False


def test_send_message_streams_agent_response(sqlite_session, monkeypatch_context: pytest.MonkeyPatch):
    service = ChatService(sqlite_session)
    conversation = service.create_conversation("user-1", "selection")

    monkeypatch_context.setattr(chat_service_module, "get_chat_agent", lambda agent_type: DummyChatAgent())

    async def consume() -> list[str]:
        chunks: list[str] = []
        async for chunk in service.send_message(str(conversation.id), "user-1", "hello"):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(consume())
    assert chunks == ["hello", " world"]


def test_get_chat_agent_requires_registry_entry():
    with pytest.raises(ValueError):
        get_chat_agent("selection")
