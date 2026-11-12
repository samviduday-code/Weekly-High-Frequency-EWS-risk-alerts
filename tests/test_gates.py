from datetime import date

from ews.gates import check_data_age, check_repeat, digest_fingerprint
from ews.flags import DigestFlag


def test_refuses_when_monthly_older_than_75_days() -> None:
    latest = {"monthly_as_of": "2025-01-01"}
    age = check_data_age(latest, today=date(2026, 11, 12))
    assert age.refuse is True
    assert age.reason == "stale_data"


def test_mentions_when_older_than_60_but_not_refused() -> None:
    latest = {"monthly_as_of": "2026-09-01"}
    age = check_data_age(latest, today=date(2026, 11, 12))
    assert age.refuse is False
    assert age.mention_samvid is True


def test_duplicate_repeat_guard() -> None:
    flags = [
        DigestFlag("a", "P1", None, {}),
    ]
    fp = digest_fingerprint(flags)
    last = {"week_iso": "2026-W46", "digest_hash": fp}
    repeat = check_repeat(week_stamp="2026-W46", fingerprint=fp, last_post=last)
    assert repeat.duplicate is True
