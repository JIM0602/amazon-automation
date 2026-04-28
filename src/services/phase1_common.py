"""Shared helpers for phase-1 dashboard and ads services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date
    previous_start: date
    previous_end: date


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def resolve_date_window(
    time_range: str = "site_today",
    start_date: str | None = None,
    end_date: str | None = None,
) -> DateWindow:
    today = today_utc()
    if time_range == "custom":
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start is None or end is None:
            raise ValueError("custom time_range requires start_date and end_date")
    elif time_range in {"site_today", "last_24h"}:
        start = end = today
    elif time_range == "this_week":
        start = today - timedelta(days=today.weekday())
        end = today
    elif time_range == "this_month":
        start = today.replace(day=1)
        end = today
    elif time_range == "this_year":
        start = today.replace(month=1, day=1)
        end = today
    else:
        start = end = today

    if end < start:
        start, end = end, start

    days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return DateWindow(start=start, end=end, previous_start=previous_start, previous_end=previous_end)


def safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round((current - previous) / previous * 100.0, 2)


def metric_card(current: float, previous: float) -> dict[str, float]:
    return {
        "value": round(current, 4),
        "change_percentage": percent_change(current, previous),
    }


def paginate(items: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    total = len(items)
    start = max(page - 1, 0) * page_size
    return items[start:start + page_size], total


def sort_items(
    items: list[dict[str, Any]],
    sort_by: str,
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    reverse = sort_order.lower() != "asc"

    def key_func(item: dict[str, Any]) -> Any:
        value = item.get(sort_by)
        return (value is None, value)

    return sorted(items, key=key_func, reverse=reverse)


def first_value(row: Any, names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if isinstance(row, dict):
            value = row.get(name)
        else:
            value = getattr(row, name, None)
        if value is not None:
            return value
    return default
