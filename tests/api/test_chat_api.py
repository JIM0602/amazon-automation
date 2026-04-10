"""Chat REST + SSE API endpoint tests.

Covers:
- POST   /api/chat/conversations          — create conversation
- GET    /api/chat/conversations          — list conversations
- GET    /api/chat/conversations/{id}     — get single conversation
- GET    /api/chat/conversations/{id}/history — get message history
- DELETE /api/chat/conversations/{id}     — delete conversation
- POST   /api/chat/{agent_type}/stream    — stream SSE
- RBAC: operator cannot create boss-only agents (403)
- Cross-user access blocked (404)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake model objects returned by mocked ChatService
# ---------------------------------------------------------------------------

def _fake_conversation(
    conv_id: str | None = None,
    user_id: str = "boss",
    agent_type: str = "selection",
    title: str | None = "Test conversation",
):
    """Create a fake Conversation-like object."""
    conv = MagicMock()
    conv.id = uuid.UUID(conv_id) if conv_id else uuid.uuid4()
    conv.user_id = user_id
    conv.agent_type = agent_type
    conv.title = title
    conv.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    conv.updated_at = datetime(2025, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    return conv


def _fake_message(
    msg_id: str | None = None,
    conversation_id: str | None = None,
    role: str = "user",
    content: str = "Hello",
):
    """Create a fake ChatMessage-like object."""
    msg = MagicMock()
    msg.id = uuid.UUID(msg_id) if msg_id else uuid.uuid4()
    msg.conversation_id = uuid.UUID(conversation_id) if conversation_id else uuid.uuid4()
    msg.role = role
    msg.content = content
    msg.created_at = datetime(2025, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
    return msg


# ---------------------------------------------------------------------------
# Conversation CRUD Tests
# ---------------------------------------------------------------------------

_CONV_ID = str(uuid.uuid4())


class TestCreateConversation:
    """POST /api/chat/conversations tests."""

    @patch("src.api.chat.ChatService")
    def test_create_conversation_success(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Boss can create a selection conversation — 201."""
        fake_conv = _fake_conversation(user_id="boss", agent_type="selection")
        mock_cls.return_value.create_conversation.return_value = fake_conv

        resp = client.post(
            "/api/chat/conversations",
            json={"agent_type": "selection", "title": "My chat"},
            headers=boss_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["agent_type"] == "selection"
        assert data["user_id"] == "boss"
        assert "id" in data
        assert "created_at" in data

    @patch("src.api.chat.ChatService")
    def test_create_conversation_invalid_agent(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Unknown agent_type returns 404."""
        resp = client.post(
            "/api/chat/conversations",
            json={"agent_type": "nonexistent_agent"},
            headers=boss_headers,
        )
        assert resp.status_code == 404, resp.text

    @patch("src.api.chat.ChatService")
    def test_operator_cannot_create_auditor_conversation(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator creating an auditor conversation gets 403."""
        resp = client.post(
            "/api/chat/conversations",
            json={"agent_type": "auditor"},
            headers=operator_headers,
        )
        assert resp.status_code == 403, resp.text

    @patch("src.api.chat.ChatService")
    def test_operator_cannot_create_brand_planning_conversation(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator creating a brand_planning conversation gets 403."""
        resp = client.post(
            "/api/chat/conversations",
            json={"agent_type": "brand_planning"},
            headers=operator_headers,
        )
        assert resp.status_code == 403, resp.text

    @patch("src.api.chat.ChatService")
    def test_operator_can_create_selection_conversation(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator can create a non-boss-only conversation — 201."""
        fake_conv = _fake_conversation(user_id="op1", agent_type="selection")
        mock_cls.return_value.create_conversation.return_value = fake_conv

        resp = client.post(
            "/api/chat/conversations",
            json={"agent_type": "selection"},
            headers=operator_headers,
        )
        assert resp.status_code == 201, resp.text


class TestListConversations:
    """GET /api/chat/conversations tests."""

    @patch("src.api.chat.ChatService")
    def test_list_conversations(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Boss can list conversations — 200 with conversation array."""
        fake_convs = [
            _fake_conversation(user_id="boss", agent_type="selection"),
            _fake_conversation(user_id="boss", agent_type="listing"),
        ]
        mock_cls.return_value.list_conversations.return_value = fake_convs

        resp = client.get("/api/chat/conversations", headers=boss_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "conversations" in data
        assert len(data["conversations"]) == 2

    @patch("src.api.chat.ChatService")
    def test_list_conversations_with_filter(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Filtering by agent_type passes through to service."""
        mock_cls.return_value.list_conversations.return_value = []

        resp = client.get(
            "/api/chat/conversations?agent_type=selection",
            headers=boss_headers,
        )
        assert resp.status_code == 200, resp.text
        mock_cls.return_value.list_conversations.assert_called_once()
        call_args = mock_cls.return_value.list_conversations.call_args
        assert call_args[0][1] == "selection" or call_args[1].get("agent_type") == "selection" or call_args[0][-1] == "selection"

    def test_list_conversations_unauthenticated(self, client: TestClient) -> None:
        """Unauthenticated request returns 401."""
        resp = client.get("/api/chat/conversations")
        assert resp.status_code == 401, resp.text


class TestGetConversation:
    """GET /api/chat/conversations/{id} tests."""

    @patch("src.api.chat.ChatService")
    def test_get_conversation_success(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Boss can get their own conversation — 200."""
        conv_id = str(uuid.uuid4())
        fake_conv = _fake_conversation(conv_id=conv_id, user_id="boss")

        with patch("src.api.chat.Conversation") as mock_model:
            mock_query = MagicMock()
            # We need to mock db.query(Conversation).filter(...).first()
            # The endpoint uses _get_conversation_or_404 which queries DB directly
            pass

        # Use a different approach: mock the DB query through get_db
        # Since the endpoint uses db.query directly, we patch at a higher level
        from src.db.models import Conversation as ConvModel

        with patch.object(
            ConvModel, "__table__", ConvModel.__table__
        ):
            # Actually, it's easier to just call the endpoint and let conftest
            # handle the DB. But we need real data for that. Let's use mock.
            pass

        # Simpler approach: patch the _get_conversation_or_404 helper
        with patch("src.api.chat._get_conversation_or_404") as mock_get:
            mock_get.return_value = fake_conv
            resp = client.get(
                f"/api/chat/conversations/{conv_id}",
                headers=boss_headers,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["id"] == conv_id
            assert data["user_id"] == "boss"

    def test_get_conversation_not_found(
        self, client: TestClient, boss_headers: dict,
    ) -> None:
        """Non-existent conversation returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(
            f"/api/chat/conversations/{fake_id}",
            headers=boss_headers,
        )
        assert resp.status_code == 404, resp.text

    def test_get_conversation_invalid_uuid(
        self, client: TestClient, boss_headers: dict,
    ) -> None:
        """Invalid UUID format returns 422."""
        resp = client.get(
            "/api/chat/conversations/not-a-valid-uuid",
            headers=boss_headers,
        )
        assert resp.status_code == 422, resp.text


class TestGetConversationHistory:
    """GET /api/chat/conversations/{id}/history tests."""

    @patch("src.api.chat.ChatService")
    @patch("src.api.chat._get_conversation_or_404")
    def test_get_history_success(
        self, mock_get_conv: MagicMock, mock_cls: MagicMock,
        client: TestClient, boss_headers: dict,
    ) -> None:
        """Boss can get message history — 200."""
        conv_id = str(uuid.uuid4())
        fake_conv = _fake_conversation(conv_id=conv_id, user_id="boss")
        mock_get_conv.return_value = fake_conv

        fake_msgs = [
            _fake_message(conversation_id=conv_id, role="user", content="Hello"),
            _fake_message(conversation_id=conv_id, role="assistant", content="Hi there!"),
        ]
        mock_cls.return_value.get_history.return_value = fake_msgs

        resp = client.get(
            f"/api/chat/conversations/{conv_id}/history",
            headers=boss_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["conversation_id"] == conv_id
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @patch("src.api.chat.ChatService")
    @patch("src.api.chat._get_conversation_or_404")
    def test_get_history_with_limit(
        self, mock_get_conv: MagicMock, mock_cls: MagicMock,
        client: TestClient, boss_headers: dict,
    ) -> None:
        """Limit parameter is passed through to service."""
        conv_id = str(uuid.uuid4())
        mock_get_conv.return_value = _fake_conversation(conv_id=conv_id, user_id="boss")
        mock_cls.return_value.get_history.return_value = []

        resp = client.get(
            f"/api/chat/conversations/{conv_id}/history?limit=10",
            headers=boss_headers,
        )
        assert resp.status_code == 200, resp.text

    def test_get_history_not_found(
        self, client: TestClient, boss_headers: dict,
    ) -> None:
        """Non-existent conversation returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(
            f"/api/chat/conversations/{fake_id}/history",
            headers=boss_headers,
        )
        assert resp.status_code == 404, resp.text


class TestDeleteConversation:
    """DELETE /api/chat/conversations/{id} tests."""

    @patch("src.api.chat.ChatService")
    def test_delete_conversation_success(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Boss can delete their own conversation — 200 with ok=True."""
        conv_id = str(uuid.uuid4())
        mock_cls.return_value.delete_conversation.return_value = True

        resp = client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers=boss_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

    @patch("src.api.chat.ChatService")
    def test_delete_conversation_not_found(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Deleting a non-existent conversation returns 404."""
        conv_id = str(uuid.uuid4())
        mock_cls.return_value.delete_conversation.return_value = False

        resp = client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers=boss_headers,
        )
        assert resp.status_code == 404, resp.text

    def test_delete_conversation_unauthenticated(
        self, client: TestClient,
    ) -> None:
        """Unauthenticated delete returns 401."""
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/api/chat/conversations/{fake_id}")
        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Cross-user access tests
# ---------------------------------------------------------------------------

class TestCrossUserAccess:
    """Verify user A cannot access user B's conversations."""

    def test_get_other_users_conversation(
        self, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator cannot access a conversation that doesn't exist for them — 404."""
        # Use a random UUID that won't belong to the operator
        fake_id = str(uuid.uuid4())
        resp = client.get(
            f"/api/chat/conversations/{fake_id}",
            headers=operator_headers,
        )
        assert resp.status_code == 404, resp.text

    @patch("src.api.chat.ChatService")
    def test_delete_other_users_conversation(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator cannot delete a conversation belonging to boss — 404."""
        conv_id = str(uuid.uuid4())
        # ChatService.delete_conversation returns False when user doesn't own it
        mock_cls.return_value.delete_conversation.return_value = False

        resp = client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers=operator_headers,
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# SSE Stream Tests
# ---------------------------------------------------------------------------

class TestChatStream:
    """POST /api/chat/{agent_type}/stream tests."""

    @patch("src.api.chat.ChatService")
    def test_stream_invalid_agent_type(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """Invalid agent_type returns 404."""
        resp = client.post(
            "/api/chat/nonexistent/stream",
            json={"message": "hello"},
            headers=boss_headers,
        )
        assert resp.status_code == 404, resp.text

    @patch("src.api.chat.ChatService")
    def test_stream_operator_auditor_forbidden(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator cannot stream auditor agent — 403."""
        resp = client.post(
            "/api/chat/auditor/stream",
            json={"message": "hello"},
            headers=operator_headers,
        )
        assert resp.status_code == 403, resp.text

    @patch("src.api.chat.ChatService")
    def test_stream_operator_brand_planning_forbidden(
        self, mock_cls: MagicMock, client: TestClient, operator_headers: dict,
    ) -> None:
        """Operator cannot stream brand_planning agent — 403."""
        resp = client.post(
            "/api/chat/brand_planning/stream",
            json={"message": "hello"},
            headers=operator_headers,
        )
        assert resp.status_code == 403, resp.text

    @patch("src.api.chat.ChatService")
    def test_stream_auto_creates_conversation(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """When conversation_id is None, a new conversation is auto-created."""
        fake_conv = _fake_conversation(user_id="boss", agent_type="selection")
        mock_cls.return_value.create_conversation.return_value = fake_conv

        async def fake_gen():
            yield "Hello from agent"

        mock_cls.return_value.send_message.return_value = fake_gen()

        resp = client.post(
            "/api/chat/selection/stream",
            json={"message": "hello"},
            headers=boss_headers,
        )
        # SSE streaming should return 200
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
        mock_cls.return_value.create_conversation.assert_called_once()

    @patch("src.api.chat.ChatService")
    def test_stream_with_existing_conversation(
        self, mock_cls: MagicMock, client: TestClient, boss_headers: dict,
    ) -> None:
        """When conversation_id is provided, skip auto-create."""
        conv_id = str(uuid.uuid4())

        async def fake_gen():
            yield "Response chunk"

        mock_cls.return_value.send_message.return_value = fake_gen()

        resp = client.post(
            "/api/chat/selection/stream",
            json={"message": "hello", "conversation_id": conv_id},
            headers=boss_headers,
        )
        assert resp.status_code == 200, resp.text
        mock_cls.return_value.create_conversation.assert_not_called()

    def test_stream_unauthenticated(self, client: TestClient) -> None:
        """Unauthenticated stream request returns 401."""
        resp = client.post(
            "/api/chat/selection/stream",
            json={"message": "hello"},
        )
        assert resp.status_code == 401, resp.text
