"""Persist last emailed digest metadata for duplicate detection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ews.paths import repeat_guard_path


def load_last_post() -> dict[str, Any] | None:
    path = repeat_guard_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_last_post(
    *,
    week_iso: str,
    digest_hash: str,
    recipient: str,
) -> None:
    path = repeat_guard_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "week_iso": week_iso,
        "digest_hash": digest_hash,
        "recipient": recipient,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
