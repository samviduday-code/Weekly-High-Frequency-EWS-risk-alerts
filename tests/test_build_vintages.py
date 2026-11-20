from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data" / "build_ews_vintages.py"


def test_build_uses_latest_scored_print_on_or_before_cutoff(tmp_path: Path) -> None:
    panel = {
        "monthly_risk_index": 47.4,
        "weekly_risk_index": 32.1,
        "lending_implications": ["Keep the cutoff rule."],
        "series": [
            {
                "id_prefix": "eway_bills",
                "name": "E-way bills",
                "cadence": "monthly",
                "metric": "YoY %",
                "lending_link": "Trade throughput",
                "source": "GSTN",
                "observations": [
                    {"date": "2026-09-30", "value": 7.2, "z": -1.69, "risk": 73.7},
                    {"date": "2026-10-31", "value": 9.1},
                    {"date": "2026-11-30", "value": 99.0, "z": -2.0, "risk": 80.0},
                ],
            }
        ],
    }
    external = tmp_path / "New" / "external_hf"
    external.mkdir(parents=True)
    (external / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    script = tmp_path / "build_ews_vintages.py"
    script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env={"EWS_AS_OF": "2026-11-20"},
    )
    assert proc.returncode == 0, proc.stderr
    latest = json.loads((external / "latest.json").read_text(encoding="utf-8"))
    assert latest["monthly_as_of"] == "2026-11-20"
    assert latest["generated_at"] == "2026-11-20"
    assert latest["red_flags"] == 1
    assert latest["flags"][0]["latest"] == 7.2
    assert latest["flags"][0]["as_of"] == "2026-09-30"
    assert "Newer print 9.1 on 2026-10-31 is not scored." in latest["flags"][0]["summary"]
    assert "99.0" not in latest["flags"][0]["summary"]
