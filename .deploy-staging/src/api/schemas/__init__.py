"""API schemas package."""
from src.api.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserInfo
from src.api.schemas.agents import (
    AgentType,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatus,
    AgentRunList,
)
from src.api.schemas.chat import (
    CreateConversationRequest,
    ConversationResponse,
    MessageResponse,
    ConversationListResponse,
    MessageHistoryResponse,
    ChatStreamRequest,
    conversation_to_response,
    message_to_response,
)
from src.api.schemas.kb_review import (
    KBReviewItemResponse,
    KBReviewListResponse,
    KBReviewEditRequest,
    KBReviewRejectRequest,
    KBReviewApproveRequest,
)

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserInfo",
    "AgentType",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentRunStatus",
    "AgentRunList",
    "CreateConversationRequest",
    "ConversationResponse",
    "MessageResponse",
    "ConversationListResponse",
    "MessageHistoryResponse",
    "ChatStreamRequest",
    "conversation_to_response",
    "message_to_response",
    "KBReviewItemResponse",
    "KBReviewListResponse",
    "KBReviewEditRequest",
    "KBReviewRejectRequest",
    "KBReviewApproveRequest",
]
