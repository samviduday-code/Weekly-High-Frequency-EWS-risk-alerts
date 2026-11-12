"""Slack digest formatting."""

from __future__ import annotations

from datetime import datetime
from ews.config import SAMVID_SLACK_MENTION, SLACK_CHANNEL_NAME
from ews.flags import DigestFlag
from ews.gates import AgeCheck, monday_week_stamp
from ews.tz_util import IST


def format_weekly_digest(
    *,
    flags: list[DigestFlag],
    age: AgeCheck,
    week_stamp: str | None = None,
    mention_samvid: bool = False,
) -> str:
    week_stamp = week_stamp or monday_week_stamp()
    dt = datetime.now(IST)
    now = f"{dt.strftime('%d %b %Y')}, {dt.strftime('%H:%M')} IST"
    lines = [
        f"**HF EWS — weekly digest** (week {week_stamp} · {now})",
        f"Channel: {SLACK_CHANNEL_NAME}",
        "",
    ]
    if mention_samvid or age.mention_samvid:
        lines.append(f"{SAMVID_SLACK_MENTION} — dataset age review")
        lines.append("")
    if age.monthly_as_of is not None and age.age_days is not None:
        lines.append(
            f"Monthly dataset as of **{age.monthly_as_of.isoformat()}** "
            f"({age.age_days} days old)."
        )
        lines.append("")
    if not flags:
        lines.append("_No High_Priority flags this week._")
    else:
        lines.append("**High-priority flags**")
        for flag in flags:
            detail = flag.raw.get("summary") or flag.raw.get("message") or flag.label
            lines.append(f"• **{flag.id_prefix}** — {detail}")
    return "\n".join(lines)
