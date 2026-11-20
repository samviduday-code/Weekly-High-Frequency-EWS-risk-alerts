#!/usr/bin/env python3
"""Rebuild data/New/external_hf/latest.json from the series panel.

Each run sets the vintage cutoff to today in IST (override with EWS_AS_OF)
and keeps the latest scored print on or before that date. A newer print
without a z-score and risk index is reported, and the previous score is kept.
No print after the cutoff is used.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PANEL_PATH = ROOT / "New" / "external_hf" / "panel.json"
LATEST_PATH = ROOT / "New" / "external_hf" / "latest.json"
PREVIOUS_PATH = ROOT / "New" / "external_hf" / "previous_pull.json"
IST = timezone(timedelta(hours=5, minutes=30))


def cutoff_date() -> date:
    override = os.environ.get("EWS_AS_OF", "").strip()
    if override:
        return date.fromisoformat(override)
    return datetime.now(IST).date()


def flag_for_risk(risk: float) -> str:
    if risk >= 65:
        return "RED"
    if risk >= 50:
        return "AMBER"
    if risk >= 40:
        return "WATCH"
    return "GREEN"


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def scored_observations(series: dict, cutoff: date) -> list[dict]:
    rows = []
    for obs in series.get("observations", []):
        obs_date = parse_day(str(obs["date"]))
        if obs_date > cutoff:
            continue
        if obs.get("z") is None or obs.get("risk") is None:
            continue
        rows.append(obs)
    rows.sort(key=lambda obs: obs["date"])
    return rows


def latest_observation(series: dict, cutoff: date) -> dict | None:
    rows = [
        obs
        for obs in series.get("observations", [])
        if parse_day(str(obs["date"])) <= cutoff
    ]
    if not rows:
        return None
    return max(rows, key=lambda obs: obs["date"])


def include_flag(series: dict, level: str) -> bool:
    if level in {"RED", "AMBER"}:
        return True
    return series.get("cadence") == "weekly" and level == "WATCH"


def format_summary(series: dict, scored: dict, level: str, newer: dict | None) -> str:
    value = float(scored["value"])
    risk = float(scored["risk"])
    zed = float(scored["z"])
    as_of = str(scored["date"])
    link = series.get("lending_link") or series["name"]
    if series.get("cadence") == "weekly":
        sentence = (
            f"{level}, WoW {value:.1f}%, z {zed:.2f}, week of {as_of}. {link}."
        )
        if series.get("inverted"):
            sentence += " Inverted."
    else:
        sentence = f"{level}, {value:.1f}% YoY, z {zed:.2f}, as of {as_of}. {link}."
    note = series.get("summary_note")
    if isinstance(note, str) and note.strip():
        sentence += f" {note.strip()}"
    sentence += f" Risk index {risk:.1f}."
    if newer is not None and str(newer["date"]) != as_of:
        newer_value = float(newer["value"])
        sentence += (
            f" Newer print {newer_value:.1f} on {newer['date']} is not scored."
        )
    return sentence


def build_flag(series: dict, scored: dict, newer: dict | None) -> dict | None:
    level = flag_for_risk(float(scored["risk"]))
    if not include_flag(series, level):
        return None
    flag = {
        "id_prefix": series["id_prefix"],
        "name": series["name"],
        "priority": "High_Priority",
        "summary": format_summary(series, scored, level, newer),
        "metric": series.get("metric") or "YoY %",
        "latest": scored["value"],
        "z": scored["z"],
        "as_of": scored["date"],
        "lending_link": series.get("lending_link") or series["name"],
        "source": series.get("source") or "",
    }
    watchlist = series.get("watchlist_priority")
    if watchlist:
        flag["watchlist_priority"] = watchlist
    if series.get("cadence") == "weekly":
        flag["weekly_level"] = level
    else:
        flag["monthly_level"] = level
    return flag


def flag_level(flag: dict) -> str | None:
    level = flag.get("monthly_level") or flag.get("weekly_level")
    if isinstance(level, str):
        return level
    return None


def same_number(left: object, right: object) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return round(float(left), 4) == round(float(right), 4)
    return left == right


def movement_lines(previous: dict | None, flags: list[dict], cutoff: date) -> list[str]:
    """At most two lines on what changed since the last scored pull."""
    if not previous:
        return ["No earlier pull is stored. This run is the baseline."]
    raw_date = previous.get("data_pull_as_of") or previous.get("monthly_as_of")
    try:
        previous_label = date.fromisoformat(str(raw_date)).strftime("%d %b %Y").lstrip("0")
    except ValueError:
        previous_label = str(raw_date)
    previous_flags = {
        flag["id_prefix"]: flag
        for flag in previous.get("flags", [])
        if isinstance(flag, dict) and flag.get("id_prefix")
    }
    current_flags = {flag["id_prefix"]: flag for flag in flags}
    moved: list[str] = []
    for key in sorted(set(previous_flags) | set(current_flags)):
        before = previous_flags.get(key)
        after = current_flags.get(key)
        if before is None and after is not None:
            moved.append(f"{after['name']} is new ({flag_level(after)}, {after['latest']} as of {after['as_of']}).")
            continue
        if after is None and before is not None:
            moved.append(f"{before.get('name', key)} dropped out of the flagged set.")
            continue
        if before is None or after is None:
            continue
        changed = not (
            same_number(before.get("latest"), after.get("latest"))
            and same_number(before.get("z"), after.get("z"))
            and before.get("as_of") == after.get("as_of")
            and flag_level(before) == flag_level(after)
        )
        if changed:
            moved.append(
                f"{after['name']} {before.get('latest')} -> {after.get('latest')} "
                f"(z {before.get('z')} -> {after.get('z')}, "
                f"{flag_level(before)} -> {flag_level(after)}, as of {after.get('as_of')})."
            )
    if not moved:
        return [
            f"No scored print has moved since the {previous_label} pull.",
            (
                f"Cutoff is {cutoff.strftime('%d %b %Y').lstrip('0')}. "
                "The heatmap matches that pull because the panel has no later scored observation."
            ),
        ]
    shown = moved[:1]
    rest = len(moved) - len(shown)
    if rest:
        shown.append(f"{rest} more flagged series also moved since the {previous_label} pull.")
    else:
        shown.append(f"Compared with the {previous_label} pull. The other flagged series are unchanged.")
    return shown


def snapshot_flags(flags: list[dict], data_pull_as_of: str) -> dict:
    return {
        "data_pull_as_of": data_pull_as_of,
        "flags": [
            {
                "id_prefix": flag["id_prefix"],
                "name": flag["name"],
                "latest": flag["latest"],
                "z": flag["z"],
                "as_of": flag["as_of"],
                "monthly_level": flag.get("monthly_level"),
                "weekly_level": flag.get("weekly_level"),
            }
            for flag in flags
        ],
    }


def build_vintage(panel: dict, cutoff: date, canvas_url: str | None, previous: dict | None) -> dict:
    flags = []
    for series in panel.get("series", []):
        scored_rows = scored_observations(series, cutoff)
        if not scored_rows:
            continue
        scored = scored_rows[-1]
        newer = latest_observation(series, cutoff)
        flag = build_flag(series, scored, newer)
        if flag is not None:
            flags.append(flag)

    red_flags = sum(
        1
        for flag in flags
        if flag.get("monthly_level") == "RED" or flag.get("weekly_level") == "RED"
    )
    monthly_red_amber = sum(
        1 for flag in flags if flag.get("monthly_level") in {"RED", "AMBER"}
    )
    vintage = {
        "monthly_as_of": cutoff.isoformat(),
        "generated_at": cutoff.isoformat(),
        "monthly_risk_index": panel["monthly_risk_index"],
        "weekly_risk_index": panel["weekly_risk_index"],
        "red_flags": red_flags,
        "monthly_red_amber": monthly_red_amber,
        "vintage_note": (
            f"Vintage cutoff {cutoff.strftime('%d %b %Y').lstrip('0')}. "
            "Uses only prints available on or before that date. "
            "No forward fill of later releases."
        ),
        "lending_implications": panel.get("lending_implications") or [],
        "since_last_pull": movement_lines(previous, flags, cutoff),
        "flags": flags,
    }
    if canvas_url:
        vintage["canvas_url"] = canvas_url
    return vintage


def existing_canvas_url() -> str | None:
    if not LATEST_PATH.is_file():
        return None
    try:
        payload = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    url = payload.get("canvas_url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def load_previous() -> dict | None:
    if not PREVIOUS_PATH.is_file():
        return None
    try:
        payload = json.loads(PREVIOUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def scored_fingerprint(flags: list[dict]) -> list[tuple]:
    return [
        (
            flag["id_prefix"],
            flag.get("latest"),
            flag.get("z"),
            flag.get("as_of"),
            flag.get("monthly_level"),
            flag.get("weekly_level"),
        )
        for flag in flags
    ]


def main() -> int:
    panel = json.loads(PANEL_PATH.read_text(encoding="utf-8"))
    cutoff = cutoff_date()
    canvas_url = existing_canvas_url() or panel.get("canvas_url")
    if not isinstance(canvas_url, str):
        canvas_url = None
    previous = load_previous()
    vintage = build_vintage(panel, cutoff, canvas_url, previous)
    LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_PATH.write_text(
        json.dumps(vintage, indent=2) + "\n",
        encoding="utf-8",
    )
    if previous is None or scored_fingerprint(previous.get("flags", [])) != scored_fingerprint(vintage["flags"]):
        pull_as_of = cutoff.isoformat()
        dated = [str(flag["as_of"]) for flag in vintage["flags"]]
        if dated:
            pull_as_of = max(dated)
        PREVIOUS_PATH.write_text(
            json.dumps(snapshot_flags(vintage["flags"], pull_as_of), indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"wrote {LATEST_PATH} cutoff={cutoff.isoformat()} "
        f"flags={len(vintage['flags'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
