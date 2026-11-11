"""Monday HF EWS refresh, compare, and optional git commit."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ews.compare import diff_snapshots
from ews.ews_json import find_latest_early_warning_json, load_snapshot
from ews.format_slack import build_failure_dm, build_weekly_dm
from ews.paths import clone_or_update_index_data, external_hf_dir


@dataclass
class WeeklyResult:
    ok: bool
    pipeline_notes: list[str]
    weekly_message: str
    major_message: str | None
    committed: bool
    index_data_root: Path | None


def _run_python_script(root: Path, script_name: str, notes: list[str]) -> bool:
    script = root / script_name
    if not script.is_file():
        # common locations
        matches = list(root.rglob(script_name))
        if not matches:
            notes.append(f"Missing script: {script_name}")
            return False
        script = matches[0]
    try:
        subprocess.run(
            [os.environ.get("PYTHON", shutil.which("python3") or "python3"), str(script)],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        notes.append(f"Ran {script_name}")
        return True
    except subprocess.CalledProcessError as exc:
        notes.append(
            f"{script_name} failed: {(exc.stderr or exc.stdout or str(exc)).strip()[:500]}"
        )
        return False


def _backup_prior_json(external_hf: Path) -> Path | None:
    latest = find_latest_early_warning_json(external_hf)
    if not latest:
        return None
    backup = latest.with_suffix(latest.suffix + ".prior_week_backup")
    shutil.copy2(latest, backup)
    return backup


def _commit_external_hf(root: Path, notes: list[str]) -> bool:
    ext = external_hf_dir(root)
    if not ext.is_dir():
        notes.append("No New/external_hf directory to commit")
        return False
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "New/external_hf"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            notes.append("No changes under New/external_hf to commit")
            return False
        subprocess.run(["git", "add", "New/external_hf"], cwd=root, check=True)
        msg = os.environ.get(
            "EWS_COMMIT_MESSAGE",
            "Refresh New/external_hf EWS early_warning outputs (weekly HF run)",
        )
        subprocess.run(["git", "commit", "-m", msg], cwd=root, check=True)
        push = os.environ.get("EWS_GIT_PUSH", "1").strip() not in {"0", "false", "no"}
        if push:
            subprocess.run(["git", "push", "origin", "HEAD"], cwd=root, check=True)
        notes.append("Committed refreshed New/external_hf outputs")
        return True
    except subprocess.CalledProcessError as exc:
        notes.append(f"git commit failed: {(exc.stderr or exc.stdout or exc).strip()[:300]}")
        return False


def run_weekly() -> WeeklyResult:
    notes: list[str] = []
    root, clone_notes = clone_or_update_index_data()
    notes.extend(clone_notes)

    if not (root / ".git").is_dir() and not external_hf_dir(root).is_dir():
        msg = build_failure_dm(notes)
        return WeeklyResult(
            ok=False,
            pipeline_notes=notes,
            weekly_message=msg,
            major_message=None,
            committed=False,
            index_data_root=None,
        )

    ext = external_hf_dir(root)
    prior_path = _backup_prior_json(ext)
    prior_snap = load_snapshot(prior_path) if prior_path else None

    fetch_ok = _run_python_script(root, "fetch_new_hf_and_sep_actuals.py", notes)
    build_ok = _run_python_script(root, "build_ews_vintages.py", notes)

    latest = find_latest_early_warning_json(ext)
    if not latest:
        notes.append("No early_warning JSON found under New/external_hf/")
        msg = build_failure_dm(notes)
        return WeeklyResult(
            ok=False,
            pipeline_notes=notes,
            weekly_message=msg,
            major_message=None,
            committed=False,
            index_data_root=root,
        )

    if not fetch_ok or not build_ok:
        notes.append("Using latest available on-disk vintage after partial pipeline failure")

    curr_snap = load_snapshot(latest)
    diff = diff_snapshots(prior_snap, curr_snap)
    weekly, major = build_weekly_dm(diff, pipeline_notes=notes)

    committed = False
    if fetch_ok or build_ok:
        committed = _commit_external_hf(root, notes)

    return WeeklyResult(
        ok=True,
        pipeline_notes=notes,
        weekly_message=weekly,
        major_message=major,
        committed=committed,
        index_data_root=root,
    )


def result_to_json(result: WeeklyResult) -> str:
    return json.dumps(
        {
            "ok": result.ok,
            "pipeline_notes": result.pipeline_notes,
            "weekly_message": result.weekly_message,
            "major_message": result.major_message,
            "committed": result.committed,
            "index_data_root": str(result.index_data_root) if result.index_data_root else None,
        },
        indent=2,
    )
