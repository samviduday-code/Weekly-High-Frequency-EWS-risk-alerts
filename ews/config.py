"""Shared configuration for the HF EWS weekly pipeline."""

from __future__ import annotations

import os

# Slack delivery (monday-ews)
SLACK_CHANNEL_ID = "C0CH2MP70RF"
SLACK_CHANNEL_NAME = "#weekly-high-frequency-ews"
SAMVID_SLACK_MENTION = "<@U0C2JAUECJV>"

# Data sources
DEFAULT_INDEX_DATA_REPO = "https://github.com/samviduday-code/index-data.git"
DEFAULT_ACTUALS_REPO = "https://github.com/samviduday-code/actuals.git"

STALE_REFUSE_DAYS = 75
STALE_MENTION_DAYS = 60

FETCH_SCRIPT = "fetch_new_hf_and_sep_actuals.py"
BUILD_SCRIPT = "build_ews_vintages.py"

REPEAT_GUARD_FILE = "slack_last_post.json"


def default_index_data_dir(repo_root: str) -> str:
    env = os.environ.get("INDEX_DATA_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.join(repo_root, ".data", "index-data")
