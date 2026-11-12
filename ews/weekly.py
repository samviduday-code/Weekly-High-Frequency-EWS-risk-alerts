"""Weekly orchestration for HF EWS Monday digest."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Literal

from ews.digest import format_weekly_digest, weekly_subject
from ews.flags import filter_high_priority_flags
from ews.gates import (
    AgeCheck,
    RepeatCheck,
    check_data_age,
    check_repeat,
    digest_fingerprint,
    monday_week_stamp,
)
from ews.index_data import (
    BuildOutcome,
    extract_flags,
    load_latest_json,
    run_fetch_and_build,
)
from ews.email_delivery import EmailDeliveryError, send_digest
from ews.repeat_guard import load_last_post, save_last_post

Reason = Literal[
    "ok",
    "fetch_failed",
    "stale_data",
    "duplicate_digest",
    "missing_latest",
    "email_failed",
]


@dataclass(frozen=True)
class WeeklyResult:
    exit_code: int
    reason: Reason
    message: str
    digest: str | None = None
    posted: bool = False


def run_weekly(
    *,
    post_email: bool = False,
    skip_fetch: bool = False,
) -> WeeklyResult:
    build: BuildOutcome = run_fetch_and_build(skip_fetch=skip_fetch)
    if not build.ok:
        return WeeklyResult(
            exit_code=1,
            reason="fetch_failed",
            message=build.message,
        )

    try:
        latest = load_latest_json(build.index_data_dir)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return WeeklyResult(
            exit_code=1,
            reason="missing_latest",
            message=str(exc),
        )

    age: AgeCheck = check_data_age(latest)
    flags = filter_high_priority_flags(extract_flags(latest))
    week_stamp = monday_week_stamp()
    fingerprint = digest_fingerprint(flags)

    if age.refuse:
        return WeeklyResult(
            exit_code=0,
            reason="stale_data",
            message=f"skipped: {age.reason} (monthly as-of {age.monthly_as_of})",
        )

    repeat: RepeatCheck = check_repeat(
        week_stamp=week_stamp,
        fingerprint=fingerprint,
        last_post=load_last_post(),
    )
    if repeat.duplicate:
        digest = format_weekly_digest(
            flags=flags,
            age=age,
            week_stamp=week_stamp,
            mention_samvid=True,
            latest=latest,
        )
        return WeeklyResult(
            exit_code=0,
            reason="duplicate_digest",
            message="skipped: duplicate digest for this calendar week",
            digest=digest if post_email else None,
        )

    mention = age.mention_samvid
    digest = format_weekly_digest(
        flags=flags,
        age=age,
        week_stamp=week_stamp,
        mention_samvid=mention,
        latest=latest,
    )

    if not post_email:
        print(digest, file=sys.stdout)
        return WeeklyResult(exit_code=0, reason="ok", message="digest written to stdout", digest=digest)

    try:
        recipient = send_digest(subject=weekly_subject(week_stamp), body=digest)
    except EmailDeliveryError as exc:
        return WeeklyResult(
            exit_code=1,
            reason="email_failed",
            message=str(exc),
            digest=digest,
        )

    save_last_post(
        week_iso=week_stamp,
        digest_hash=fingerprint,
        recipient=recipient,
    )
    return WeeklyResult(
        exit_code=0,
        reason="ok",
        message=f"emailed {recipient}",
        digest=digest,
        posted=True,
    )
