"""High-priority flag filtering for the Monday digest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _priority(flag: dict[str, Any]) -> str:
    return str(flag.get("priority") or flag.get("Priority") or "")


def _is_high_priority(flag: dict[str, Any]) -> bool:
    return _priority(flag) == "High_Priority"


def _level_key(flag: dict[str, Any]) -> tuple[bool, bool]:
    monthly = flag.get("monthly_level") not in (None, "", "None")
    weekly = flag.get("weekly_level") not in (None, "", "None")
    return monthly, weekly


@dataclass(frozen=True)
class DigestFlag:
    id_prefix: str
    monthly_level: str | None
    weekly_level: str | None
    raw: dict[str, Any]

    @property
    def label(self) -> str:
        if self.monthly_level:
            return f"monthly={self.monthly_level}"
        if self.weekly_level:
            return f"weekly={self.weekly_level}"
        return "level=n/a"


def id_prefix(flag: dict[str, Any]) -> str:
    for key in ("id_prefix", "id", "indicator_id", "name"):
        val = flag.get(key)
        if val:
            return str(val)
    return "unknown"


def filter_high_priority_flags(flags: list[dict[str, Any]]) -> list[DigestFlag]:
    """Keep High_Priority rows with a monthly or weekly level; one row per id_prefix."""
    by_prefix: dict[str, tuple[DigestFlag, bool]] = {}
    for flag in flags:
        if not _is_high_priority(flag):
            continue
        monthly, weekly = _level_key(flag)
        if not monthly and not weekly:
            continue
        prefix = id_prefix(flag)
        digest = DigestFlag(
            id_prefix=prefix,
            monthly_level=str(flag["monthly_level"]) if monthly else None,
            weekly_level=str(flag["weekly_level"]) if weekly else None,
            raw=flag,
        )
        has_monthly = monthly
        existing = by_prefix.get(prefix)
        if existing is None:
            by_prefix[prefix] = (digest, has_monthly)
            continue
        # Prefer monthly over weekly when both exist for the same prefix.
        if has_monthly and not existing[1]:
            by_prefix[prefix] = (digest, has_monthly)
    return [pair[0] for _, pair in sorted(by_prefix.items(), key=lambda x: x[0])]
