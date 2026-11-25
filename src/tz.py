"""Israel time helpers. The server runs in UTC and timestamps are stored as naive UTC
(datetime.now() / SQLite datetime('now')); everything a person SEES or is scheduled by
must be Israel time (handles DST)."""
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    IL = ZoneInfo("Asia/Jerusalem")
except Exception:                      # tzdata missing: fixed UTC+3 fallback (summer time)
    IL = timezone(timedelta(hours=3))


def il_now() -> datetime:
    return datetime.now(IL)


def il_today() -> date:
    return il_now().date()


def utc_to_il(value) -> datetime:
    """Naive datetime / ISO string stored as UTC -> aware Israel datetime."""
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace(" ", "T"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IL)
