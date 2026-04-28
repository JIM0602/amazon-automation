"""Manual phase-1 data sync endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.db.connection import get_db
from src.services.ads_sync_service import sync_ads
from src.services.sales_sync_service import sync_sales


router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/ads")
async def trigger_ads_sync(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return sync_ads(db, start_date=start_date, end_date=end_date)


@router.post("/sales")
async def trigger_sales_sync(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return sync_sales(db, start_date=start_date, end_date=end_date)
