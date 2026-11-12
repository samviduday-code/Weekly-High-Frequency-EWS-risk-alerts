from ews.flags import filter_high_priority_flags


def test_prefers_monthly_over_weekly_for_same_prefix() -> None:
    flags = [
        {
            "id_prefix": "x",
            "priority": "High_Priority",
            "weekly_level": "P2",
        },
        {
            "id_prefix": "x",
            "priority": "High_Priority",
            "monthly_level": "P1",
            "weekly_level": "P2",
        },
    ]
    out = filter_high_priority_flags(flags)
    assert len(out) == 1
    assert out[0].monthly_level == "P1"


def test_skips_non_high_priority() -> None:
    out = filter_high_priority_flags(
        [{"id_prefix": "a", "priority": "Low_Priority", "monthly_level": "P1"}]
    )
    assert out == []
