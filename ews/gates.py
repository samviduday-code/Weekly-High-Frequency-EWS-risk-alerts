"""Staleness and repeat guards."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from ews.config import STALE_MENTION_DAYS, STALE_REFUSE_DAYS
from ews.flags import DigestFlag
from ews.tz_util import IST


@dataclass(frozen=True)
class AgeCheck:
    monthly_as_of: date | None
    age_days: int | None
    refuse: bool
    mention_samvid: bool
    reason: str | None = None


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text[:10]):
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d-%b-%Y"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    return None


def monthly_as_of_from_latest(latest: dict[str, Any]) -> date | None:
    for key in (
        "monthly_as_of",
        "latest_monthly_date",
        "monthly_dataset_date",
        "as_of_monthly",
    ):
        parsed = parse_date(latest.get(key))
        if parsed:
            return parsed
    parsed = parse_date(latest.get("as_of"))
    if parsed:
        return parsed
    return parse_date(latest.get("generated_at"))


def check_data_age(latest: dict[str, Any], *, today: date | None = None) -> AgeCheck:
    today = today or datetime.now(IST).date()
    monthly_as_of = monthly_as_of_from_latest(latest)
    if monthly_as_of is None:
        return AgeCheck(
            monthly_as_of=None,
            age_days=None,
            refuse=True,
            mention_samvid=True,
            reason="missing_monthly_as_of",
        )
    age_days = (today - monthly_as_of).days
    refuse = age_days > STALE_REFUSE_DAYS
    mention = age_days > STALE_MENTION_DAYS
    reason = "stale_data" if refuse else None
    return AgeCheck(
        monthly_as_of=monthly_as_of,
        age_days=age_days,
        refuse=refuse,
        mention_samvid=mention,
        reason=reason,
    )


def monday_week_stamp(today: date | None = None) -> str:
    """Label for the week that contains the Monday run (ISO week, IST)."""
    today = today or datetime.now(IST).date()
  # Monday of this calendar week
    monday = today - timedelta(days=today.weekday())
    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def digest_fingerprint(flags: list[DigestFlag]) -> str:
    payload = [
        {
            "id_prefix": f.id_prefix,
            "monthly_level": f.monthly_level,
            "weekly_level": f.weekly_level,
        }
        for f in flags
    ]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class RepeatCheck:
    duplicate: bool
    reason: str | None = None


def check_repeat(
    *,
    week_stamp: str,
    fingerprint: str,
    last_post: dict[str, Any] | None,
) -> RepeatCheck:
    if not last_post:
        return RepeatCheck(duplicate=False)
    if last_post.get("week_iso") != week_stamp:
        return RepeatCheck(duplicate=False)
    if last_post.get("digest_hash") == fingerprint:
        return RepeatCheck(duplicate=True, reason="duplicate_digest")
    return RepeatCheck(duplicate=False)
