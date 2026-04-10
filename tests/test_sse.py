"""Tests for src.api.sse — SSE formatting utilities."""
from __future__ import annotations

import asyncio
import json

from src.api.sse import (
    EVENT_DONE,
    EVENT_ERROR,
    EVENT_MESSAGE,
    format_sse_event,
    sse_response,
)


# --------------------------------------------------------------------------- #
#  format_sse_event
# --------------------------------------------------------------------------- #


class TestFormatSseEvent:
    """Tests for :func:`format_sse_event`."""

    def test_basic_data_frame(self):
        """Produces ``data: {json}\\n\\n`` without event type."""
        result = format_sse_event({"type": EVENT_MESSAGE, "content": "hello"})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        payload = json.loads(result.removeprefix("data: ").rstrip("\n"))
        assert payload == {"type": "message", "content": "hello"}

    def test_with_event_type(self):
        """Produces ``event: <type>\\ndata: {json}\\n\\n`` when event_type given."""
        result = format_sse_event({"type": EVENT_DONE}, event_type="done")
        lines = result.split("\n")
        assert lines[0] == "event: done"
        assert lines[1].startswith("data: ")
        payload = json.loads(lines[1].removeprefix("data: "))
        assert payload == {"type": "done"}
        # Must end with double newline
        assert result.endswith("\n\n")

    def test_unicode_content(self):
        """Non-ASCII content is preserved (ensure_ascii=False)."""
        result = format_sse_event({"content": "你好世界"})
        payload = json.loads(result.removeprefix("data: ").rstrip("\n"))
        assert payload["content"] == "你好世界"

    def test_empty_dict(self):
        """Empty dict is still valid JSON."""
        result = format_sse_event({})
        assert result == "data: {}\n\n"


# --------------------------------------------------------------------------- #
#  sse_response
# --------------------------------------------------------------------------- #


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


async def _collect_body(resp) -> str:
    """Drain a StreamingResponse body_iterator into a string."""
    body = b""
    async for part in resp.body_iterator:
        body += part.encode() if isinstance(part, str) else part
    return body.decode()


class TestSseResponse:
    """Tests for :func:`sse_response`."""

    def test_returns_streaming_response(self):
        """Returns a StreamingResponse with correct media type and headers."""

        async def _test():
            async def gen():
                yield "hi"

            resp = await sse_response(gen(), conversation_id="conv-1")
            assert resp.media_type == "text/event-stream"
            assert resp.headers.get("cache-control") == "no-cache"
            assert resp.headers.get("x-accel-buffering") == "no"

        _run(_test())

    def test_stream_content(self):
        """Chunks are wrapped as SSE message events, ending with done."""

        async def _test():
            async def gen():
                yield "chunk-1"
                yield "chunk-2"

            resp = await sse_response(gen(), conversation_id="conv-1")
            text = await _collect_body(resp)
            frames = [f for f in text.split("\n\n") if f.strip()]

            # Should have: message(chunk-1), message(chunk-2), done
            assert len(frames) == 3

            msg1 = json.loads(frames[0].removeprefix("data: "))
            assert msg1["type"] == EVENT_MESSAGE
            assert msg1["content"] == "chunk-1"

            msg2 = json.loads(frames[1].removeprefix("data: "))
            assert msg2["type"] == EVENT_MESSAGE
            assert msg2["content"] == "chunk-2"

            done = json.loads(frames[2].removeprefix("data: "))
            assert done["type"] == EVENT_DONE
            assert done["conversation_id"] == "conv-1"

        _run(_test())

    def test_conv_id_metadata_marker(self):
        """Special ``[CONV_ID:...]`` marker emits done with extracted id."""

        async def _test():
            async def gen():
                yield "hello"
                yield "\n\n[CONV_ID:abc-123]"

            resp = await sse_response(gen())
            text = await _collect_body(resp)
            frames = [f for f in text.split("\n\n") if f.strip()]

            # message(hello) + done(abc-123) = 2 frames
            assert len(frames) == 2
            done = json.loads(frames[1].removeprefix("data: "))
            assert done["type"] == EVENT_DONE
            assert done["conversation_id"] == "abc-123"

        _run(_test())

    def test_error_event_on_exception(self):
        """Generator exception is caught and emitted as error event."""

        async def _test():
            async def gen():
                yield "ok"
                raise RuntimeError("boom")

            resp = await sse_response(gen())
            text = await _collect_body(resp)
            frames = [f for f in text.split("\n\n") if f.strip()]

            # message(ok) + error(boom)
            assert len(frames) == 2
            error = json.loads(frames[1].removeprefix("data: "))
            assert error["type"] == EVENT_ERROR
            assert "boom" in error["content"]

        _run(_test())
