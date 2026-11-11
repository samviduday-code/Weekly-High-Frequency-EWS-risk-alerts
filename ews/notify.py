"""Slack delivery helpers for weekly EWS (channel ID from env)."""

from __future__ import annotations

import os

# Default: Samvid Uday user DM on the workspace where Cursor Slack MCP is installed.
# Override with SLACK_DM_CHANNEL_ID when routing to a specific DM (e.g. D0C2GA3UR18).
DEFAULT_SLACK_DM_CHANNEL_ID = "U0CE0J1Q4Q2"


def slack_dm_channel_id() -> str:
    return (
        os.environ.get("SLACK_DM_CHANNEL_ID", "").strip()
        or os.environ.get("EWS_SLACK_CHANNEL_ID", "").strip()
        or DEFAULT_SLACK_DM_CHANNEL_ID
    )
