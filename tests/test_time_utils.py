from scout_engine.time_utils import display_ist, to_utc_iso


def test_edT_deadline_normalizes_across_calendar_day():
    utc = to_utc_iso("2026-09-19T23:45:00", "America/New_York")
    assert utc.startswith("2026-09-20T03:45:00")
    assert display_ist(utc) == "2026-09-20 09:15 IST"
