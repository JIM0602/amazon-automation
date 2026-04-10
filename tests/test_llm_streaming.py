"""LLM 流式接口测试。"""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_rate_limiter():
    limiter = MagicMock()
    limiter.acquire_or_raise.return_value = SimpleNamespace(allowed=True)
    return limiter


@pytest.fixture
def mock_daily_limit_ok():
    return {
        "daily_cost": 0.0,
        "limit": 50.0,
        "percentage": 0.0,
        "exceeded": False,
        "warning": False,
    }


class _AsyncOpenAIStream:
    def __init__(self, chunks, usage=None, model="gpt-4o-mini"):
        self._chunks = chunks
        self.usage = usage
        self.model = model

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield chunk


class _AnthropicStreamContext:
    def __init__(self, chunks, final_message):
        self._chunks = chunks
        self._final_message = final_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    @property
    def text_stream(self):
        async def _iter():
            for chunk in self._chunks:
                yield chunk

        return _iter()

    def get_final_message(self):
        return self._final_message


@pytest.mark.asyncio
async def test_chat_stream_openai_yields_chunks_and_tracks_usage(mock_rate_limiter, mock_daily_limit_ok):
    from src.llm.client import chat_stream

    usage = SimpleNamespace(prompt_tokens=12, completion_tokens=7)
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="world"))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
    ]
    stream = _AsyncOpenAIStream(chunks=chunks, usage=usage, model="gpt-4o-mini")

    mock_client = MagicMock()
    mock_client.chat.completions.create = MagicMock(return_value=stream)

    openai_module = types.SimpleNamespace(AsyncOpenAI=MagicMock(return_value=mock_client))

    with patch.dict(sys.modules, {"openai": openai_module}), \
         patch("src.llm.client.get_rate_limiter", return_value=mock_rate_limiter), \
         patch("src.llm.client.check_daily_limit", return_value=mock_daily_limit_ok), \
         patch("src.llm.client._track_usage", return_value=0.001) as mock_track, \
         patch("src.llm.client._record_agent_run") as mock_record, \
         patch("src.llm.client.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        parts = []
        async for piece in chat_stream([
            {"role": "user", "content": "Hello"}
        ], model="gpt-4o-mini"):
            parts.append(piece)

    assert parts == ["Hello ", "world"]
    mock_rate_limiter.acquire_or_raise.assert_called_once()
    mock_track.assert_called_once_with(
        model="gpt-4o-mini",
        input_tokens=12,
        output_tokens=7,
        agent_type="llm_stream",
    )
    mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_chat_stream_anthropic_yields_chunks(mock_rate_limiter, mock_daily_limit_ok):
    from src.llm.client import chat_stream

    usage = SimpleNamespace(input_tokens=9, output_tokens=4)
    final_message = SimpleNamespace(usage=usage, model="claude-3-5-sonnet")
    stream_ctx = _AnthropicStreamContext(chunks=["foo", "bar"], final_message=final_message)

    anthropic_client = MagicMock()
    anthropic_client.messages.stream = MagicMock(return_value=stream_ctx)
    anthropic_module = types.SimpleNamespace(AsyncAnthropic=MagicMock(return_value=anthropic_client))

    with patch.dict(sys.modules, {"anthropic": anthropic_module}), \
         patch("src.llm.client.get_rate_limiter", return_value=mock_rate_limiter), \
         patch("src.llm.client.check_daily_limit", return_value=mock_daily_limit_ok), \
         patch("src.llm.client._track_usage", return_value=0.001) as mock_track, \
         patch("src.llm.client._record_agent_run") as mock_record, \
         patch("src.llm.client.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.ANTHROPIC_API_KEY = "anthropic-test"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        parts = []
        async for piece in chat_stream(
            [{"role": "user", "content": "Hello"}],
            model="claude-3-5-sonnet",
        ):
            parts.append(piece)

    assert parts == ["foo", "bar"]
    mock_track.assert_called_once_with(
        model="claude-3-5-sonnet",
        input_tokens=9,
        output_tokens=4,
        agent_type="llm_stream",
    )
    mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_chat_stream_yields_error_message_on_failure(mock_rate_limiter, mock_daily_limit_ok):
    from src.llm.client import chat_stream

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")
    openai_module = types.SimpleNamespace(AsyncOpenAI=MagicMock(return_value=mock_client))

    with patch.dict(sys.modules, {"openai": openai_module}), \
         patch("src.llm.client.get_rate_limiter", return_value=mock_rate_limiter), \
         patch("src.llm.client.check_daily_limit", return_value=mock_daily_limit_ok), \
         patch("src.llm.client.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        parts = []
        async for piece in chat_stream([
            {"role": "user", "content": "Hello"}
        ], model="gpt-4o-mini"):
            parts.append(piece)

    assert len(parts) == 1
    assert "[Error: boom]" in parts[0]
