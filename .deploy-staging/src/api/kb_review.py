import logging
from datetime import datetime, timezone
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import require_role
from src.api.schemas.kb_review import (
    KBReviewApproveRequest,
    KBReviewEditRequest,
    KBReviewItemResponse,
    KBReviewListResponse,
    KBReviewRejectRequest,
)
from src.db import get_db
from src.db.models import KBReviewQueue
from src.knowledge_base.rag_engine import RAGEngine

router = APIRouter(prefix="/api/kb-review", tags=["kb-review"])
logger = logging.getLogger(__name__)


def _item_to_response(item: KBReviewQueue) -> KBReviewItemResponse:
    item_any = cast(Any, item)
    return KBReviewItemResponse(
        id=str(item_any.id),
        content=item_any.content,
        source=item_any.source,
        agent_type=item_any.agent_type,
        summary=item_any.summary,
        status=item_any.status,
        reviewer_id=item_any.reviewer_id,
        review_comment=item_any.review_comment,
        created_at=item_any.created_at.isoformat() if item_any.created_at else "",
        reviewed_at=item_any.reviewed_at.isoformat() if item_any.reviewed_at else None,
    )


@router.get("", response_model=KBReviewListResponse)
async def list_kb_review_items(
    status: str = Query(default="pending"),
    agent_type: Optional[str] = Query(default=None),
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> KBReviewListResponse:
    query = db.query(KBReviewQueue).filter(KBReviewQueue.status == status)
    if agent_type:
        query = query.filter(KBReviewQueue.agent_type == agent_type)
    
    items = query.order_by(KBReviewQueue.created_at.desc()).all()
    
    return KBReviewListResponse(
        items=[_item_to_response(item) for item in items],
        total=len(items)
    )


@router.post("/{item_id}/approve", response_model=KBReviewItemResponse)
async def approve_kb_review_item(
    item_id: str,
    body: KBReviewApproveRequest,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> KBReviewItemResponse:
    item = db.query(KBReviewQueue).filter(KBReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KB review item not found")
        
    item_any = cast(Any, item)
    if item_any.status != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item_any.status}")

    item_any.status = "approved"
    item_any.reviewer_id = current_user["username"]
    item_any.reviewed_at = datetime.now(timezone.utc)
    if body.comment:
        item_any.review_comment = body.comment
        
    db.commit()
    db.refresh(item)
    
    # Try to write to knowledge base using RAGEngine
    try:
        rag_engine = RAGEngine()
        chunk = {
            "content": item_any.content,
            "metadata": {
                "source": item_any.source,
                "agent_type": item_any.agent_type,
                "summary": item_any.summary,
            }
        }
        rag_engine.ingest_chunks([chunk])
    except Exception as e:
        logger.error(f"Failed to ingest approved KB item {item_id}: {e}")
        # Even if ingest fails, the item remains approved according to requirements

    return _item_to_response(item)


@router.post("/{item_id}/reject", response_model=KBReviewItemResponse)
async def reject_kb_review_item(
    item_id: str,
    body: KBReviewRejectRequest,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> KBReviewItemResponse:
    item = db.query(KBReviewQueue).filter(KBReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KB review item not found")
        
    item_any = cast(Any, item)
    if item_any.status != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item_any.status}")

    item_any.status = "rejected"
    item_any.reviewer_id = current_user["username"]
    item_any.review_comment = body.comment
    item_any.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(item)
    
    return _item_to_response(item)


@router.put("/{item_id}", response_model=KBReviewItemResponse)
async def edit_kb_review_item(
    item_id: str,
    body: KBReviewEditRequest,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> KBReviewItemResponse:
    item = db.query(KBReviewQueue).filter(KBReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KB review item not found")
        
    item_any = cast(Any, item)
    if item_any.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending items can be edited")

    item_any.content = body.content
    if body.summary is not None:
        item_any.summary = body.summary
        
    db.commit()
    db.refresh(item)
    
    return _item_to_response(item)
