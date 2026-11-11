"""Load and interpret early_warning JSON (flexible schema)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


FLAG_ORDER = {"GREEN": 0, "OK": 0, "NEUTRAL": 0, "WATCH": 1, "AMBER": 2, "RED": 3}


@dataclass
class SeriesPoint:
    key: str
    name: str
    priority: str
    flag: str
    z: float | None
    latest: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EwsSnapshot:
    path: Path
    raw: dict[str, Any]
    as_of: str
    stance: str
    composite_monthly: float | None
    composite_weekly: float | None
    series: list[SeriesPoint]

    def by_key(self) -> dict[str, SeriesPoint]:
        return {s.key: s for s in self.series}


def find_latest_early_warning_json(external_hf: Path) -> Path | None:
    if not external_hf.is_dir():
        return None
    candidates = sorted(
        external_hf.rglob("*early_warning*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = sorted(
            external_hf.rglob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    return candidates[0] if candidates else None


def load_snapshot(path: Path) -> EwsSnapshot:
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_snapshot(path, data)


def _parse_snapshot(path: Path, data: dict[str, Any]) -> EwsSnapshot:
    as_of = _first_str(data, ["as_of", "asOf", "vintage", "run_date", "date"]) or path.stem
    stance = (_first_str(data, ["stance", "overall_stance", "posture"]) or "UNKNOWN").upper()

    composite_monthly = _first_number(
        data,
        [
            "composite_monthly_risk",
            "compositeMonthlyRisk",
            "monthly_risk",
            "composite.risk_monthly",
        ],
    )
    composite_weekly = _first_number(
        data,
        [
            "composite_weekly_risk",
            "compositeWeeklyRisk",
            "weekly_risk",
            "composite.risk_weekly",
        ],
    )

    comp = data.get("composite")
    if isinstance(comp, dict):
        if composite_monthly is None:
            composite_monthly = _coerce_number(
                comp.get("monthly_risk") or comp.get("monthly") or comp.get("monthlyRisk")
            )
        if composite_weekly is None:
            composite_weekly = _coerce_number(
                comp.get("weekly_risk") or comp.get("weekly") or comp.get("weeklyRisk")
            )

    series = _collect_series(data)
    return EwsSnapshot(
        path=path,
        raw=data,
        as_of=as_of,
        stance=stance,
        composite_monthly=composite_monthly,
        composite_weekly=composite_weekly,
        series=series,
    )


def _collect_series(data: dict[str, Any]) -> list[SeriesPoint]:
    found: list[SeriesPoint] = []

    for bucket_key in ("series", "indicators", "signals", "metrics"):
        bucket = data.get(bucket_key)
        if isinstance(bucket, list):
            for item in bucket:
                if isinstance(item, dict):
                    pt = _series_from_dict(item)
                    if pt:
                        found.append(pt)
        elif isinstance(bucket, dict):
            for key, item in bucket.items():
                if isinstance(item, dict):
                    pt = _series_from_dict(item, key=key)
                    if pt:
                        found.append(pt)

    # Top-level named P1 blocks
    for key, item in data.items():
        if key in {"series", "indicators", "signals", "metrics", "composite", "meta"}:
            continue
        if isinstance(item, dict) and any(
            k in item for k in ("flag", "z", "z_score", "latest", "value", "priority")
        ):
            pt = _series_from_dict(item, key=key)
            if pt:
                found.append(pt)

    dedup: dict[str, SeriesPoint] = {}
    for pt in found:
        dedup[pt.key] = pt
    return list(dedup.values())


def _series_from_dict(item: dict[str, Any], key: str = "") -> SeriesPoint | None:
    series_id = (
        key
        or _first_str(item, ["id", "key", "code", "series_id", "name"])
        or ""
    ).strip()
    if not series_id:
        return None

    name = _first_str(item, ["name", "label", "title", "series"]) or series_id
    priority = (_first_str(item, ["priority", "tier", "p_level"]) or "").upper()
    flag = (_first_str(item, ["flag", "status", "alert", "band", "risk_flag"]) or "GREEN").upper()
    z = _first_number(item, ["z", "z_score", "zscore", "standard_score"])
    latest = _first_str(item, ["latest", "latest_print", "value", "print", "last_value"]) or "n/a"

    extra = {k: v for k, v in item.items() if k not in {"name", "flag", "z", "latest"}}
    return SeriesPoint(
        key=series_id.lower().replace(" ", "_"),
        name=name,
        priority=priority,
        flag=flag,
        z=z,
        latest=latest,
        extra=extra,
    )


def _first_str(data: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        if "." in key:
            val = _dig(data, key)
        else:
            val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _first_number(data: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        if "." in key:
            val = _dig(data, key)
        else:
            val = data.get(key)
        num = _coerce_number(val)
        if num is not None:
            return num
    return None


def _dig(data: dict[str, Any], dotted: str) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _coerce_number(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def flag_at_least(flag: str, threshold: str) -> bool:
    return FLAG_ORDER.get(flag.upper(), 0) >= FLAG_ORDER.get(threshold.upper(), 99)


def is_p1_series(pt: SeriesPoint) -> bool:
    if pt.priority in {"P1", "1"}:
        return True
    name_l = pt.name.lower()
    key_l = pt.key.lower()
    p1_tokens = (
        "ics",
        "atm",
        "aeps",
        "nach",
        "cash",
        "industrial_confidence",
        "consumer_sentiment",
    )
    return any(tok in name_l or tok in key_l for tok in p1_tokens)


def lending_implication(pt: SeriesPoint) -> str:
    key = pt.key
    if "ics" in key or "sentiment" in key or "confidence" in key:
        return "Tighter underwriting if sentiment stays soft; watch early delinquency."
    if "atm" in key or "aeps" in key or "cash" in key:
        return "Liquidity stress can lift defaults; monitor cash-dependent borrowers."
    if "nach" in key:
        return "Debit stress signals repayment friction; watch EMI bounce rates."
    if pt.flag == "RED":
        return "Elevated macro/credit headwind; defensive growth and collections focus."
    return "Monitor series; adjust triggers if deterioration persists."
