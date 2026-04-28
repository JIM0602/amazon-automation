"""Minimal SP-API sales sync chain for phase 1."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.amazon_sp_api import OrdersApi, SpApiAuth, SpApiClient
from src.config import settings
from src.db.models import SalesDaily, Sku, SyncJob
from src.services.phase1_common import safe_float, safe_int


STORE_TOTAL_SKU = "__store_total__"


def _sp_client() -> SpApiClient:
    has_credentials = all([
        settings.AMAZON_SP_API_CLIENT_ID,
        settings.AMAZON_SP_API_CLIENT_SECRET,
        settings.AMAZON_SP_API_REFRESH_TOKEN,
    ])
    auth = SpApiAuth(
        client_id=settings.AMAZON_SP_API_CLIENT_ID or "",
        client_secret=settings.AMAZON_SP_API_CLIENT_SECRET or "",
        refresh_token=settings.AMAZON_SP_API_REFRESH_TOKEN or "",
        dry_run=settings.DRY_RUN or not has_credentials,
    )
    return SpApiClient(
        auth=auth,
        marketplace_id=settings.AMAZON_MARKETPLACE_ID,
        region="us",
        dry_run=settings.DRY_RUN or not has_credentials,
    )


def sync_sales(db: Session, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    job = SyncJob(
        job_name="amazon_sp_api_sales_minimal_sync",
        job_type="sales",
        status="running",
        records_count=0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    records = 0
    try:
        now = datetime.now(timezone.utc)
        end = datetime.fromisoformat(end_date).date() if end_date else now.date()
        start = datetime.fromisoformat(start_date).date() if start_date else end - timedelta(days=1)
        client = _sp_client()
        orders_api = OrdersApi(client)
        _ensure_store_sku(db)

        current = start
        while current <= end:
            next_day = current + timedelta(days=1)
            metrics = orders_api.get_order_metrics(
                granularity="Day",
                start_date=f"{current.isoformat()}T00:00:00Z",
                end_date=f"{next_day.isoformat()}T00:00:00Z",
                marketplace_id=settings.AMAZON_MARKETPLACE_ID,
            )
            row = db.execute(
                select(SalesDaily).where(
                    SalesDaily.date == current,
                    SalesDaily.sku == STORE_TOTAL_SKU,
                    SalesDaily.marketplace == settings.AMAZON_MARKETPLACE_ID,
                    SalesDaily.snapshot_type == "t0",
                )
            ).scalar_one_or_none()
            if row is None:
                row = SalesDaily(
                    date=current,
                    sku=STORE_TOTAL_SKU,
                    marketplace=settings.AMAZON_MARKETPLACE_ID,
                    snapshot_type="t0",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(row)
            row.sales_amount = safe_float(metrics.get("total_revenue"))
            row.order_count = safe_int(metrics.get("total_orders"))
            row.units_sold = safe_int(metrics.get("total_units") or metrics.get("total_orders"))
            row.currency = "USD"
            row.source = "sp_api_order_metrics"
            records += 1
            current = next_day

        job.status = "success"
        job.records_count = records
        job.finished_at = datetime.now(timezone.utc)
        job.extra_payload = {
            "dry_run": client.dry_run,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "grain": "store_total",
            "sku_level_sales_available": False,
            "note": "sales/v1/orderMetrics returns marketplace aggregate metrics; SKU ranking excludes __store_total__ until SKU-level sales source is connected.",
        }
        return {"status": "success", "records_count": records, "dry_run": client.dry_run}
    except Exception as exc:
        job.status = "failed"
        job.records_count = records
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        raise


def _ensure_store_sku(db: Session) -> None:
    row = db.execute(select(Sku).where(Sku.sku == STORE_TOTAL_SKU)).scalar_one_or_none()
    if row is None:
        now = datetime.now(timezone.utc)
        db.add(Sku(sku=STORE_TOTAL_SKU, asin=None, marketplace=settings.AMAZON_MARKETPLACE_ID, image_url=None, is_active=True, created_at=now, updated_at=now))
