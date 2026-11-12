from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from ews import gates
from ews.paths import repeat_guard_path
from ews.weekly import run_weekly

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "index_data"


@pytest.fixture()
def index_data_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "index-data"
    shutil.copytree(FIXTURE_ROOT, target)
    monkeypatch.setenv("INDEX_DATA_DIR", str(target))
    return target


def test_weekly_stdout_happy_path(index_data_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gates, "monday_week_stamp", lambda: "2026-W46")
    result = run_weekly(post_slack=False, skip_fetch=False)
    assert result.exit_code == 0
    assert result.reason == "ok"
    assert result.digest is not None
    assert "credit_growth" in result.digest
    assert "liquidity" in result.digest


def test_weekly_missing_index_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("INDEX_DATA_DIR", str(missing))
    result = run_weekly(post_slack=False, skip_fetch=True)
    assert result.exit_code == 1
    assert result.reason == "fetch_failed"


def test_weekly_stale_gate(index_data_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    latest_path = index_data_tmp / "New" / "external_hf" / "latest.json"
    data = json.loads(latest_path.read_text(encoding="utf-8"))
    data["monthly_as_of"] = "2020-01-01"
    latest_path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(gates, "check_data_age", lambda _latest: gates.AgeCheck(
        monthly_as_of=date(2020, 1, 1),
        age_days=2000,
        refuse=True,
        mention_samvid=True,
        reason="stale_data",
    ))
    result = run_weekly(post_slack=False, skip_fetch=True)
    assert result.exit_code == 0
    assert result.reason == "stale_data"


def test_duplicate_skips_post(index_data_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gates, "monday_week_stamp", lambda: "2026-W46")
    first = run_weekly(post_slack=False, skip_fetch=True)
    assert first.reason == "ok"
    guard = repeat_guard_path()
    guard.parent.mkdir(parents=True, exist_ok=True)
    from ews.flags import filter_high_priority_flags
    from ews.gates import digest_fingerprint
    from ews.index_data import extract_flags, load_latest_json

    latest = load_latest_json(index_data_tmp)
    flags = filter_high_priority_flags(extract_flags(latest))
    guard.write_text(
        json.dumps(
            {
                "week_iso": "2026-W46",
                "digest_hash": digest_fingerprint(flags),
                "channel_id": "C0CH2MP70RF",
            }
        ),
        encoding="utf-8",
    )
    second = run_weekly(post_slack=False, skip_fetch=True)
    assert second.exit_code == 0
    assert second.reason == "duplicate_digest"
