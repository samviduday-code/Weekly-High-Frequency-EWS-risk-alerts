"""Plain-text weekly digest formatting."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from ews.config import digest_recipient
from ews.flags import DigestFlag
from ews.gates import AgeCheck, monday_week_stamp
from ews.tz_util import IST


def weekly_subject(week_stamp: str) -> str:
    return f"HF EWS — weekly digest (week {week_stamp})"


def _headline(latest: dict[str, Any] | None) -> list[str]:
    if not latest:
        return []
    lines: list[str] = []
    note = latest.get("vintage_note")
    if isinstance(note, str) and note.strip():
        lines.append(note.strip())
    monthly = latest.get("monthly_risk_index")
    weekly = latest.get("weekly_risk_index")
    if monthly is not None or weekly is not None:
        parts: list[str] = []
        if monthly is not None:
            parts.append(f"Monthly risk index {monthly} (0-100)")
        if weekly is not None:
            parts.append(f"Weekly risk index {weekly} (0-100)")
        lines.append(". ".join(parts) + ".")
    reds = latest.get("red_flags")
    amber = latest.get("monthly_red_amber")
    if reds is not None and amber is not None:
        lines.append(f"RED flags (monthly and weekly): {reds}. Monthly RED+AMBER: {amber}.")
    if lines:
        lines.append("")
    return lines


def _implications(latest: dict[str, Any] | None) -> list[str]:
    if not latest:
        return []
    notes = latest.get("lending_implications")
    if not isinstance(notes, list) or not notes:
        return []
    lines = ["", "Lending implications"]
    for note in notes:
        if isinstance(note, str) and note.strip():
            lines.append(f"- {note.strip()}")
    return lines


def format_weekly_digest(
    *,
    flags: list[DigestFlag],
    age: AgeCheck,
    week_stamp: str | None = None,
    mention_samvid: bool = False,
    latest: dict[str, Any] | None = None,
) -> str:
    week_stamp = week_stamp or monday_week_stamp()
    dt = datetime.now(IST)
    now = f"{dt.strftime('%d %b %Y')}, {dt.strftime('%H:%M')} IST"
    lines = [
        f"HF EWS — weekly digest (week {week_stamp} · {now})",
        "",
    ]
    lines.extend(_headline(latest))
    if mention_samvid or age.mention_samvid:
        lines.append(f"Dataset age review for {digest_recipient()}")
        lines.append("")
    if age.monthly_as_of is not None and age.age_days is not None:
        lines.append(
            f"Monthly dataset as of {age.monthly_as_of.isoformat()} "
            f"({age.age_days} days old)."
        )
        lines.append("")
    if not flags:
        lines.append("No High_Priority flags this week.")
    else:
        lines.append("High-priority flags")
        for flag in flags:
            detail = flag.raw.get("summary") or flag.raw.get("message") or flag.label
            lines.append(f"- {flag.id_prefix} — {detail}")
    lines.extend(_implications(latest))
    return "\n".join(lines)
