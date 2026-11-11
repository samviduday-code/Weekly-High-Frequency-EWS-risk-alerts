import json
from pathlib import Path

from ews.compare import diff_snapshots, major_risk_triggers
from ews.ews_json import load_snapshot


def test_major_risk_on_red(tmp_path: Path) -> None:
    prev = {
        "stance": "GREEN",
        "composite": {"monthly_risk": 30, "weekly_risk": 20},
        "series": [{"id": "ics", "name": "ICS", "priority": "P1", "flag": "GREEN", "z": 0.2, "latest": "100"}],
    }
    curr = {
        "stance": "AMBER",
        "composite": {"monthly_risk": 40, "weekly_risk": 35},
        "series": [{"id": "ics", "name": "ICS", "priority": "P1", "flag": "RED", "z": -2.1, "latest": "98"}],
    }
    p = tmp_path / "prev.json"
    c = tmp_path / "curr.json"
    p.write_text(json.dumps(prev))
    c.write_text(json.dumps(curr))
    diff = diff_snapshots(load_snapshot(p), load_snapshot(c))
    assert major_risk_triggers(diff)
