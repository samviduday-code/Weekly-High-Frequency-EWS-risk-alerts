"""IST timezone helper (works without system tzdata)."""

from __future__ import annotations

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

try:
    IST = ZoneInfo("Asia/Calcutta")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))
