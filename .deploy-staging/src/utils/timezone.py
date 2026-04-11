"""Site timezone utilities (US = America/Los_Angeles)."""

from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _load_site_tz(site: str) -> tzinfo:
    if site == "US":
        try:
            return ZoneInfo("America/Los_Angeles")
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=-8), name="America/Los_Angeles")
    return timezone.utc


SITE_TZ = {
    "US": _load_site_tz("US"),
}


def now_site_time(site: str = "US") -> datetime:
    """Return current time in site timezone (timezone-aware)."""
    return datetime.now(tz=SITE_TZ.get(site, SITE_TZ["US"]))


def to_site_time(dt: datetime, site: str = "US") -> datetime:
    """Convert a datetime to site timezone. If naive, assume UTC."""
    tz = SITE_TZ.get(site, SITE_TZ["US"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def site_today_range(site: str = "US") -> tuple[datetime, datetime]:
    """Return (start_of_today, end_of_today) in site timezone."""
    now = now_site_time(site)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def last_24h_range(site: str = "US") -> tuple[datetime, datetime]:
    """Return (24h ago, now) in site timezone."""
    from datetime import timedelta

    end = now_site_time(site)
    start = end - timedelta(hours=24)
    return start, end


def week_range(site: str = "US") -> tuple[datetime, datetime]:
    """Return (start_of_week_monday, end_of_now) in site timezone."""
    from datetime import timedelta

    now = now_site_time(site)
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def month_range(site: str = "US") -> tuple[datetime, datetime]:
    """Return (start_of_month, end_of_now) in site timezone."""
    now = now_site_time(site)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def year_range(site: str = "US") -> tuple[datetime, datetime]:
    """Return (start_of_year, end_of_now) in site timezone."""
    now = now_site_time(site)
    start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now
