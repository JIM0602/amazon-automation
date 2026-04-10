"""SSE (Server-Sent Events) formatting utilities.

Provides helpers for formatting SSE events and wrapping async generators
into FastAPI StreamingResponse objects with proper headers for real-time
streaming through Nginx.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# SSE event types
EVENT_MESSAGE = "message"
EVENT_THINKING = "thinking"
EVENT_TOOL_CALL = "tool_call"
EVENT_ERROR = "error"
EVENT_DONE = "done"
EVENT_HEARTBEAT = "heartbeat"

# Heartbeat interval in seconds — keeps Nginx/proxy from closing idle SSE connections
HEARTBEAT_INTERVAL_S = 15


def format_sse_event(data: dict[str, Any], event_type: str | None = None) -> str:
    """Format a dict as an SSE event string: ``data: {json}\\n\\n``.

    Args:
        data: Payload dict to JSON-serialise.
        event_type: Optional SSE ``event:`` field.

    Returns:
        A correctly formatted SSE frame.
    """
    payload = json.dumps(data, ensure_ascii=False)
    if event_type:
        return f"event: {event_type}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


def _heartbeat_comment() -> str:
    """Return an SSE comment line used as a keep-alive ping.

    SSE comments (lines starting with ``:``) are silently ignored by
    compliant EventSource clients but reset proxy idle timers.
    """
    return ": heartbeat\n\n"


async def sse_response(
    generator: AsyncGenerator[str, None],
    conversation_id: str | None = None,
) -> StreamingResponse:
    """Wrap an async generator into an SSE StreamingResponse with heartbeat.

    The generator yields plain-text chunks. Each chunk is wrapped into an SSE
    ``data:`` frame of type ``message``. A ``done`` event is emitted after the
    generator is exhausted, and an ``error`` event if an exception occurs.

    A heartbeat comment (``: heartbeat``) is emitted every
    :data:`HEARTBEAT_INTERVAL_S` seconds of inactivity to prevent Nginx and
    other reverse proxies from closing the connection.

    Special metadata convention: if a chunk starts with ``\\n\\n[CONV_ID:``
    the conversation id is extracted and sent inside the ``done`` event.

    Args:
        generator: Async generator producing text chunks.
        conversation_id: Optional conversation id echoed in the ``done`` event.

    Returns:
        A :class:`StreamingResponse` suitable for FastAPI route handlers.
    """

    async def event_stream():  # noqa: C901
        try:
            ait = generator.__aiter__()
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        ait.__anext__(), timeout=HEARTBEAT_INTERVAL_S,
                    )
                except asyncio.TimeoutError:
                    # No data within the heartbeat window — send keep-alive
                    yield _heartbeat_comment()
                    continue
                except StopAsyncIteration:
                    break

                if chunk.startswith("\n\n[CONV_ID:"):
                    # Extract conversation_id from metadata marker
                    conv_id = chunk.strip().removeprefix("[CONV_ID:").rstrip("]")
                    yield format_sse_event({"type": EVENT_DONE, "conversation_id": conv_id})
                    return
                yield format_sse_event({"type": EVENT_MESSAGE, "content": chunk})

            # Send done event after generator exhaustion
            yield format_sse_event({"type": EVENT_DONE, "conversation_id": conversation_id})
        except Exception as e:
            logger.error("SSE stream error: %s", e)
            yield format_sse_event({"type": EVENT_ERROR, "content": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Tell Nginx not to buffer
        },
    )
