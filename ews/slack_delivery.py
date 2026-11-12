"""Optional Slack Web API delivery."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ews.config import SLACK_CHANNEL_ID


class SlackDeliveryError(RuntimeError):
    pass


def post_message(*, text: str, channel_id: str | None = None) -> str:
    token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_USER_TOKEN")
    if not token:
        raise SlackDeliveryError(
            "SLACK_BOT_TOKEN or SLACK_USER_TOKEN is required for --post-slack"
        )
    channel_id = channel_id or SLACK_CHANNEL_ID
    payload = json.dumps(
        {"channel": channel_id, "text": text, "mrkdwn": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SlackDeliveryError(f"Slack API request failed: {exc}") from exc
    if not body.get("ok"):
        raise SlackDeliveryError(
            f"Slack API error: {body.get('error', 'unknown')}"
        )
    return str(body.get("ts", ""))
