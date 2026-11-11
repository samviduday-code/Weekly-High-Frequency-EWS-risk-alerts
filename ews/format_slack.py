"""Slack message formatting for weekly EWS."""

from __future__ import annotations

from datetime import datetime, timezone

from ews.compare import EwsDiff, major_risk_triggers, slight_risk_triggers
from ews.ews_json import EwsSnapshot, flag_at_least, is_p1_series, lending_implication


def _fmt_z(z: float | None) -> str:
    return f"{z:.2f}" if z is not None else "n/a"


def _top_flags(snap: EwsSnapshot, limit: int = 6) -> list[str]:
    ranked = sorted(
        snap.series,
        key=lambda s: (
            -{"RED": 3, "AMBER": 2, "WATCH": 1}.get(s.flag, 0),
            -(s.z if s.z is not None else 0),
        ),
    )
    lines = []
    for s in ranked[:limit]:
        if flag_at_least(s.flag, "WATCH"):
            lines.append(f"• {s.name}: {s.flag} (z={_fmt_z(s.z)}, latest={s.latest})")
    return lines


def _p1_watchlist(snap: EwsSnapshot) -> list[str]:
    lines = []
    for s in snap.series:
        if not is_p1_series(s):
            continue
        lines.append(
            f"• {s.name}: {s.flag} (z={_fmt_z(s.z)}, latest={s.latest})"
        )
    if not lines:
        lines.append("• (no P1 series matched in JSON — check ICS/ATM-AePS/NACH fields)")
    return lines


def build_weekly_dm(
    diff: EwsDiff,
    *,
    pipeline_notes: list[str],
    run_at: datetime | None = None,
) -> tuple[str, str | None]:
    """Return (weekly_message, major_risk_message_or_none)."""
    run_at = run_at or datetime.now(timezone.utc)
    snap = diff.curr
    header = f"*HF EWS — weekly summary* ({run_at.strftime('%Y-%m-%d %Z')})"
    as_of = snap.as_of

    lines = [
        header,
        f"As-of vintage: `{as_of}`",
        "",
        f"*Stance:* {snap.stance}",
        f"*Composite risk:* monthly={snap.composite_monthly if snap.composite_monthly is not None else 'n/a'}, weekly={snap.composite_weekly if snap.composite_weekly is not None else 'n/a'}",
        "",
        "*Top flags*",
        *(_top_flags(snap) or ["• None at WATCH+"]),
        "",
        "*P1 watchlist* (ICS; ATM/AePS; NACH debit value & volume)",
        *_p1_watchlist(snap),
    ]

    if pipeline_notes:
        lines.extend(["", "*Pipeline notes*", *[f"• {n}" for n in pipeline_notes]])

    if diff.prev:
        slight_bits: list[str] = []
        for ch in diff.p1_p2_newly_watch():
            slight_bits.append(
                f"P1/P2 newly WATCH+: {ch.name} ({ch.prev_flag}→{ch.curr_flag})"
            )
        for ch in diff.z_softened():
            slight_bits.append(
                f"z softened ≥0.5: {ch.name} ({_fmt_z(ch.prev_z)}→{_fmt_z(ch.curr_z)})"
            )
        for ch in diff.new_amber_series():
            slight_bits.append(f"new AMBER: {ch.name}")
        if slight_bits:
            lines.extend(["", "*WoW deterioration (explicit)*", *[f"• {b}" for b in slight_bits]])
    else:
        lines.extend(["", "_Prior-week JSON unavailable — WoW diff skipped._"])

    weekly = "\n".join(lines)

    major: str | None = None
    if major_risk_triggers(diff):
        major_lines = [
            ":rotating_light: *MAJOR RISK — HF EWS*",
            f"As-of: `{as_of}` | stance {snap.stance} | composite monthly={snap.composite_monthly}",
            "",
        ]
        for s in diff.red_flags():
            major_lines.append(
                f"• *RED* {s.name}: z={_fmt_z(s.z)}, latest={s.latest} — {lending_implication(s)}"
            )
        if diff.amber_monthly_count() >= 3:
            major_lines.append(
                f"• ≥3 monthly AMBER flags ({diff.amber_monthly_count()}) — broaden monitoring."
            )
        if snap.composite_monthly is not None and snap.composite_monthly >= 55:
            major_lines.append(
                f"• Composite monthly risk {snap.composite_monthly:.1f} (≥55) — defensive stance."
            )
        if diff.simultaneous_stress():
            major_lines.append(
                "• Simultaneous ICS softness + cash-stress (ATM/AePS) + NACH weakness."
            )
        # Detail lines for stressed P1 if not already RED
        for s in snap.series:
            if is_p1_series(s) and flag_at_least(s.flag, "WATCH"):
                major_lines.append(
                    f"• {s.name}: {s.flag}, z={_fmt_z(s.z)}, latest={s.latest} — {lending_implication(s)}"
                )
        major = "\n".join(major_lines)

    if slight_risk_triggers(diff) and not major:
        weekly += "\n\n_Slight risk: WoW deterioration triggered (see above)._"

    return weekly, major


def build_failure_dm(pipeline_notes: list[str]) -> str:
    run_at = datetime.now(timezone.utc)
    lines = [
        f"*HF EWS — weekly summary* ({run_at.strftime('%Y-%m-%d %Z')})",
        "",
        "*Status:* pipeline could not produce a fresh EWS vintage this run.",
        "",
        "*Pipeline notes*",
        *[f"• {n}" for n in pipeline_notes],
        "",
        "No risk metrics were invented. Configure `INDEX_DATA_DIR` or grant Cloud Agent access to `navi-corp/index-data` (main), then rerun `python -m ews weekly`.",
    ]
    return "\n".join(lines)
