from pydantic import BaseModel

class KBReviewItemResponse(BaseModel):
    id: str
    content: str
    source: str | None
    agent_type: str | None
    summary: str | None
    status: str
    reviewer_id: str | None
    review_comment: str | None
    created_at: str
    reviewed_at: str | None

class KBReviewListResponse(BaseModel):
    items: list[KBReviewItemResponse]
    total: int

class KBReviewEditRequest(BaseModel):
    content: str
    summary: str | None = None

class KBReviewRejectRequest(BaseModel):
    comment: str

class KBReviewApproveRequest(BaseModel):
    comment: str | None = None
