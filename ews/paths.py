"""Resolve index-data workspace paths."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

DEFAULT_REPO = "navi-corp/index-data"
DEFAULT_BRANCH = "main"


def index_data_root() -> Path:
    env = os.environ.get("INDEX_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(os.environ.get("INDEX_DATA_WORKDIR", "/tmp/index-data")).resolve()


def external_hf_dir(root: Path) -> Path:
    return root / "New" / "external_hf"


def clone_or_update_index_data() -> tuple[Path, list[str]]:
    """Clone or pull index-data; return root and human-readable status notes."""
    notes: list[str] = []
    root = index_data_root()
    repo = os.environ.get("INDEX_DATA_REPO", DEFAULT_REPO).strip()
    branch = os.environ.get("INDEX_DATA_BRANCH", DEFAULT_BRANCH).strip()

    if (root / ".git").is_dir():
        try:
            subprocess.run(
                ["git", "fetch", "origin", branch],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "pull", "--ff-only", "origin", branch],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            notes.append(f"Updated existing clone at {root}")
            return root, notes
        except subprocess.CalledProcessError as exc:
            notes.append(f"git update failed at {root}: {exc.stderr or exc.stdout or exc}")
            return root, notes

    root.parent.mkdir(parents=True, exist_ok=True)
    if root.exists() and any(root.iterdir()):
        notes.append(f"Non-git directory already exists at {root}; skipping clone")
        return root, notes

    url = os.environ.get("INDEX_DATA_GIT_URL", f"https://github.com/{repo}.git")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, url, str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        notes.append(f"Cloned {repo} ({branch}) to {root}")
    except subprocess.CalledProcessError as exc:
        notes.append(
            f"Clone failed for {url}: {(exc.stderr or exc.stdout or str(exc)).strip()}"
        )
    return root, notes
