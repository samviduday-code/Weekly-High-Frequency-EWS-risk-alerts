"""Path helpers for index-data layout."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def external_hf_dir(index_data_dir: str | os.PathLike[str]) -> Path:
    return Path(index_data_dir) / "New" / "external_hf"


def latest_json_path(index_data_dir: str | os.PathLike[str]) -> Path:
    return external_hf_dir(index_data_dir) / "latest.json"


def repeat_guard_path() -> Path:
    return repo_root() / ".ews" / "slack_last_post.json"
