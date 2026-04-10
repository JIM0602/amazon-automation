"""Tests for chat DB CRUD helpers."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.chat import add_message, create_conversation, get_conversation_history, list_user_conversations
from src.db.models import Base, ChatMessage, Conversation


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


def test_create_conversation(sqlite_session):
    conversation = create_conversation(sqlite_session, user_id="user-1", agent_type="chat", title="Hello")

    assert conversation.id is not None
    assert conversation.user_id == "user-1"
    assert conversation.agent_type == "chat"
    assert conversation.title == "Hello"
    assert sqlite_session.query(Conversation).count() == 1


def test_add_message(sqlite_session):
    conversation = create_conversation(sqlite_session, user_id="user-1", agent_type="chat")

    message = add_message(
        sqlite_session,
        conversation_id=conversation.id,
        role="user",
        content="Hi",
        metadata={"source": "test"},
    )

    assert message.id is not None
    assert message.conversation_id == conversation.id
    assert message.role == "user"
    assert message.content == "Hi"
    assert message.metadata_json == {"source": "test"}
    assert sqlite_session.query(ChatMessage).count() == 1


def test_get_conversation_history(sqlite_session):
    conversation = create_conversation(sqlite_session, user_id="user-1", agent_type="chat")
    first = add_message(sqlite_session, conversation.id, "user", "first")
    second = add_message(sqlite_session, conversation.id, "assistant", "second")

    history = get_conversation_history(sqlite_session, conversation.id)

    assert [m.id for m in history] == [first.id, second.id]
    assert [m.content for m in history] == ["first", "second"]


def test_list_user_conversations(sqlite_session):
    old_conv = create_conversation(sqlite_session, user_id="user-1", agent_type="chat", title="old")
    new_conv = create_conversation(sqlite_session, user_id="user-1", agent_type="chat", title="new")
    other_user = create_conversation(sqlite_session, user_id="user-2", agent_type="chat", title="other")
    filtered = create_conversation(sqlite_session, user_id="user-1", agent_type="support", title="support")

    conversations = list_user_conversations(sqlite_session, "user-1")
    filtered_conversations = list_user_conversations(sqlite_session, "user-1", agent_type="support")

    assert [c.id for c in conversations] == [filtered.id, new_conv.id, old_conv.id]
    assert other_user.id not in [c.id for c in conversations]
    assert [c.id for c in filtered_conversations] == [filtered.id]
