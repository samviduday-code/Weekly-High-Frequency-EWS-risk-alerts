"""Week-over-week EWS diff."""

from __future__ import annotations

from dataclasses import dataclass

from ews.ews_json import EwsSnapshot, SeriesPoint, flag_at_least, is_p1_series


@dataclass
class SeriesChange:
    key: str
    name: str
    priority: str
    prev_flag: str
    curr_flag: str
    prev_z: float | None
    curr_z: float | None
    latest: str

    @property
    def newly_watch_or_worse(self) -> bool:
        return flag_at_least(self.curr_flag, "WATCH") and not flag_at_least(
            self.prev_flag, "WATCH"
        )

    @property
    def z_softened_by_half(self) -> bool:
        if self.prev_z is None or self.curr_z is None:
            return False
        return (self.prev_z - self.curr_z) >= 0.5

    @property
    def new_amber(self) -> bool:
        return self.curr_flag == "AMBER" and self.prev_flag != "AMBER"


@dataclass
class EwsDiff:
    prev: EwsSnapshot | None
    curr: EwsSnapshot
    series_changes: list[SeriesChange]

    def p1_p2_newly_watch(self) -> list[SeriesChange]:
        out = []
        for ch in self.series_changes:
            if not ch.newly_watch_or_worse:
                continue
            pri = ch.priority.upper()
            if pri in {"P1", "P2", "1", "2"}:
                out.append(ch)
        return out

    def z_softened(self) -> list[SeriesChange]:
        return [c for c in self.series_changes if c.z_softened_by_half]

    def new_amber_series(self) -> list[SeriesChange]:
        return [c for c in self.series_changes if c.new_amber]

    def red_flags(self) -> list[SeriesPoint]:
        return [s for s in self.curr.series if s.flag == "RED"]

    def amber_monthly_count(self) -> int:
        # Monthly series often tagged in name/key; fallback: all AMBER
        monthly = [
            s
            for s in self.curr.series
            if s.flag == "AMBER"
            and any(t in s.key for t in ("m_", "_m", "monthly", "mom", "yoy"))
        ]
        if monthly:
            return len(monthly)
        return sum(1 for s in self.curr.series if s.flag == "AMBER")

    def simultaneous_stress(self) -> bool:
        ics_soft = _series_stressed(self.curr, ("ics", "sentiment", "confidence"))
        cash_soft = _series_stressed(self.curr, ("atm", "aeps", "cash"))
        nach_weak = _series_stressed(self.curr, ("nach",))
        return ics_soft and cash_soft and nach_weak


def diff_snapshots(prev: EwsSnapshot | None, curr: EwsSnapshot) -> EwsDiff:
    prev_map = prev.by_key() if prev else {}
    curr_map = curr.by_key()
    keys = sorted(set(prev_map) | set(curr_map))
    changes: list[SeriesChange] = []
    for key in keys:
        p = prev_map.get(key)
        c = curr_map.get(key)
        if not c:
            continue
        changes.append(
            SeriesChange(
                key=key,
                name=c.name,
                priority=c.priority or (p.priority if p else ""),
                prev_flag=p.flag if p else "GREEN",
                curr_flag=c.flag,
                prev_z=p.z if p else None,
                curr_z=c.z,
                latest=c.latest,
            )
        )
    return EwsDiff(prev=prev, curr=curr, series_changes=changes)


def _series_stressed(snap: EwsSnapshot, tokens: tuple[str, ...]) -> bool:
    for s in snap.series:
        if not any(t in s.key for t in tokens) and not any(
            t in s.name.lower() for t in tokens
        ):
            continue
        if flag_at_least(s.flag, "WATCH"):
            return True
        if s.z is not None and s.z <= -0.5:
            return True
    return False


def slight_risk_triggers(diff: EwsDiff) -> bool:
    if diff.p1_p2_newly_watch():
        return True
    if diff.z_softened():
        return True
    if diff.new_amber_series():
        return True
    return False


def major_risk_triggers(diff: EwsDiff) -> bool:
    if diff.red_flags():
        return True
    if diff.amber_monthly_count() >= 3:
        return True
    cm = diff.curr.composite_monthly
    if cm is not None and cm >= 55:
        return True
    if diff.simultaneous_stress():
        return True
    return False
