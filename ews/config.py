"""Shared configuration for the HF EWS weekly pipeline."""

from __future__ import annotations

import os

# Email delivery. Recipient defaults to the automation owner.
DEFAULT_DIGEST_EMAIL = "samvid.uday@navi.com"

# Data sources
DEFAULT_INDEX_DATA_REPO = "https://github.com/samviduday-code/index-data.git"
DEFAULT_ACTUALS_REPO = "https://github.com/samviduday-code/actuals.git"

STALE_REFUSE_DAYS = 75
STALE_MENTION_DAYS = 60

FETCH_SCRIPT = "fetch_new_hf_and_sep_actuals.py"
BUILD_SCRIPT = "build_ews_vintages.py"

REPEAT_GUARD_FILE = "email_last_post.json"


def digest_recipient() -> str:
    return os.environ.get("EWS_EMAIL_TO", DEFAULT_DIGEST_EMAIL).strip()


def _discover_index_data_dir(repo_root: str) -> str | None:
    candidates = [
        os.environ.get("INDEX_DATA_DIR"),
        os.path.join(repo_root, ".data", "index-data"),
        "/agent/repos/index-data",
        "/agent/repos/Index-data",
        os.path.join(os.path.dirname(repo_root), "index-data"),
    ]
    for raw in candidates:
        if not raw:
            continue
        path = os.path.abspath(raw)
        if os.path.isdir(path) and (
            os.path.isdir(os.path.join(path, "New", "external_hf"))
            or os.path.isdir(os.path.join(path, ".git"))
        ):
            return path
    return None


def default_index_data_dir(repo_root: str) -> str:
    discovered = _discover_index_data_dir(repo_root)
    if discovered:
        return discovered
    env = os.environ.get("INDEX_DATA_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.join(repo_root, "data")
