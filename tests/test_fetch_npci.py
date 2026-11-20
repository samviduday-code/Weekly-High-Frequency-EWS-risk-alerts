from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data" / "fetch_new_hf_and_sep_actuals.py"


def test_fetch_adds_only_complete_sunday_weeks(tmp_path: Path) -> None:
    external = tmp_path / "New" / "external_hf"
    external.mkdir(parents=True)
    panel = {
        "series": [
            {
                "id_prefix": "atm_nfs_volume",
                "cadence": "weekly",
                "observations": [{"date": "2026-10-04", "value": 11.1}],
            }
        ]
    }
    (external / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    # Week of 11 Oct is complete. Week of 18 Oct has only Monday, so it stays out.
    header = [
        "date",
        "AePS cash withdrawals, number of transactions, daily",
        "FASTag (NETC) toll and parking, number of transactions, daily",
        "NACH debit, value, daily",
        "IMPS, value, daily",
        "UPI, number of transactions, daily",
        "UPI, value, daily",
        "IMPS, number of transactions, daily",
        "NACH debit, number of transactions, daily",
        "ATM network (NFS) transactions, number of transactions, daily",
    ]
    csv_path = tmp_path / "npci.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for day, value in (
            ("2026-09-28", "10"),
            ("2026-10-04", "10"),
            ("2026-10-05", "20"),
            ("2026-10-11", "20"),
            ("2026-10-12", "50"),
        ):
            writer.writerow([day] + ["0"] * 8 + [value])
    script = tmp_path / "fetch_new_hf_and_sep_actuals.py"
    script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env={"NPCI_DAILY_CSV": str(csv_path), "NPCI_DAILY_URL": "", "NPCI_FETCH": "0"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    updated = json.loads((external / "panel.json").read_text(encoding="utf-8"))
    observations = updated["series"][0]["observations"]
    assert [obs["date"] for obs in observations] == ["2026-10-04", "2026-10-11"]
    assert observations[1]["value"] == 100.0
