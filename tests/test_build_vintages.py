from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data" / "build_ews_vintages.py"


def test_build_scores_the_latest_print_on_or_before_cutoff(tmp_path: Path) -> None:
    panel = {
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
                    {"date": "2026-08-31", "value": 10},
                    {"date": "2026-09-30", "value": 8},
                    {"date": "2026-10-31", "value": 4},
                    {"date": "2026-11-30", "value": 99},
                ],
            }
        ],
    }
    external = tmp_path / "New" / "external_hf"
    external.mkdir(parents=True)
    (external / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    (external / "previous_pull.json").write_text(
        json.dumps(
            {
                "data_pull_as_of": "2026-10-30",
                "flags": [
                    {
                        "id_prefix": "eway_bills",
                        "name": "E-way bills",
                        "latest": 6.0,
                        "z": -1.2,
                        "as_of": "2026-08-31",
                        "monthly_level": "AMBER",
                        "weekly_level": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
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
    assert latest["flags"][0]["latest"] == 4
    assert latest["flags"][0]["as_of"] == "2026-10-31"
    assert latest["flags"][0]["z"] < 0
    assert latest["flags"][0]["monthly_level"] == "RED"
    assert "99" not in latest["flags"][0]["summary"]
    assert latest["since_last_pull"][0].startswith("E-way bills 6.0 -> 4")
    assert "1 more" not in latest["since_last_pull"][1]
    assert "30 Oct 2026" in latest["since_last_pull"][1]
