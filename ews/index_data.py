"""Bootstrap, fetch, and load index-data artifacts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ews.config import BUILD_SCRIPT, DEFAULT_INDEX_DATA_REPO, FETCH_SCRIPT
from ews.config import default_index_data_dir
from ews.paths import latest_json_path, repo_root


@dataclass(frozen=True)
class BuildOutcome:
    ok: bool
    message: str
    index_data_dir: Path


def resolve_index_data_dir() -> Path:
    return Path(default_index_data_dir(str(repo_root())))


def ensure_index_data_present(index_data_dir: Path) -> BuildOutcome:
    if index_data_dir.is_dir() and any(index_data_dir.iterdir()):
        return BuildOutcome(True, "index-data directory present", index_data_dir)
    return BuildOutcome(
        False,
        f"index-data missing at {index_data_dir}; run scripts/bootstrap_index_data.sh "
        f"(clone {DEFAULT_INDEX_DATA_REPO})",
        index_data_dir,
    )


def _run_script(index_data_dir: Path, script_name: str) -> tuple[int, str]:
    script = index_data_dir / script_name
    if not script.is_file():
        # Allow scripts under a scripts/ subfolder
        alt = index_data_dir / "scripts" / script_name
        if alt.is_file():
            script = alt
        else:
            return 127, f"script not found: {script_name}"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=index_data_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, combined.strip() or f"exit {proc.returncode}"


def run_fetch_and_build(*, skip_fetch: bool = False) -> BuildOutcome:
    index_data_dir = resolve_index_data_dir()
    present = ensure_index_data_present(index_data_dir)
    if not present.ok:
        return present

    if not skip_fetch:
        code, msg = _run_script(index_data_dir, FETCH_SCRIPT)
        if code != 0:
            return BuildOutcome(False, f"{FETCH_SCRIPT} failed: {msg}", index_data_dir)

    code, msg = _run_script(index_data_dir, BUILD_SCRIPT)
    if code != 0:
        return BuildOutcome(False, f"{BUILD_SCRIPT} failed: {msg}", index_data_dir)

    return BuildOutcome(True, "fetch and build completed", index_data_dir)


def load_latest_json(index_data_dir: Path | None = None) -> dict:
    root = index_data_dir or resolve_index_data_dir()
    path = latest_json_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"latest.json not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_flags(latest: dict) -> list[dict]:
    for key in ("flags", "alerts", "ews_flags", "high_frequency"):
        val = latest.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
    return []
