from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest


def test_chat_base_agent_is_abstract():
    from src.agents.chat_base_agent import ChatBaseAgent

    with pytest.raises(TypeError):
        cast(Any, ChatBaseAgent)("x")


@pytest.fixture
def concrete_agent() -> Any:
    from src.agents.chat_base_agent import ChatBaseAgent

    class ConcreteChatAgent(ChatBaseAgent):
        def get_system_prompt(self) -> str:
            return "system prompt"

        def get_tools(self) -> list[object]:
            return []

        def get_model(self) -> str:
            return "gpt-4o-mini"

        @property
        def agent_type(self) -> str:
            return "chat_demo"

    return ConcreteChatAgent("demo")


def test_chat_creates_conversation_and_streams_response(concrete_agent):
    conv_id = uuid.uuid4()
    created_conversation = SimpleNamespace(id=conv_id)
    db = MagicMock()

    async def _stream(*args, **kwargs):
        yield "hello"
        yield " world"

    async def _collect():
        with patch("src.agents.chat_base_agent.create_conversation", return_value=created_conversation) as mock_create, \
         patch("src.agents.chat_base_agent.get_conversation_history", return_value=[]) as mock_history, \
         patch("src.agents.chat_base_agent.add_message") as mock_add_message, \
         patch("src.agents.chat_base_agent.chat_stream", new=_stream):

            chunks = []
            async for chunk in concrete_agent.chat("hello there", None, "user-1", db):
                chunks.append(chunk)

        return chunks, mock_create, mock_history, mock_add_message

    chunks, mock_create, mock_history, mock_add_message = asyncio.run(_collect())
    assert chunks == ["hello", " world", f"\n\n[CONV_ID:{conv_id}]"]
    mock_create.assert_called_once_with(db, "user-1", "chat_demo", title="hello there")
    mock_history.assert_called_once_with(db, conv_id, limit=50)
    assert mock_add_message.call_count == 2


def test_chat_uses_existing_conversation_history(concrete_agent):
    conv_id = uuid.uuid4()
    db = MagicMock()
    history_messages = [
        SimpleNamespace(role="user", content="earlier"),
        SimpleNamespace(role="assistant", content="reply"),
    ]

    async def _stream(messages, model=None, agent_type=None):
        yield "hello"
        yield " world"

    async def _collect():
        with patch("src.agents.chat_base_agent.create_conversation") as mock_create, \
         patch("src.agents.chat_base_agent.get_conversation_history", return_value=history_messages) as mock_history, \
         patch("src.agents.chat_base_agent.add_message") as mock_add_message, \
         patch("src.agents.chat_base_agent.chat_stream", new=_stream):

            chunks = []
            async for chunk in concrete_agent.chat("new message", str(conv_id), "user-2", db):
                chunks.append(chunk)

        return chunks, mock_create, mock_history, mock_add_message

    chunks, mock_create, mock_history, mock_add_message = asyncio.run(_collect())
    mock_create.assert_not_called()
    mock_history.assert_called_once_with(db, conv_id, limit=50)
    assert mock_add_message.call_count == 2
    assert chunks[-1] == f"\n\n[CONV_ID:{conv_id}]"
