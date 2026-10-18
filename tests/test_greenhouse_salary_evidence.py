"""Employer-sourced annual pay extraction must be conservative and auditable."""
from scout_engine.sources import greenhouse


def test_explicit_official_annual_salary_is_verified(monkeypatch):
    url = "https://job-boards.greenhouse.io/acme/jobs/1234"
    monkeypatch.setattr(
        greenhouse,
        "get_json",
        lambda _url: {
            "jobs": [
                {
                    "id": 1234,
                    "title": "Software Engineer, Early Career",
                    "absolute_url": url,
                    "content": (
                        "<p>The annual compensation range for this role is listed below.</p>"
                        "<p>Annual Salary:</p>"
                        "<p>$140,000 - $180,000 USD</p>"
                    ),
                    "location": {"name": "New York"},
                }
            ]
        },
    )
    [item] = greenhouse.GreenhouseAdapter("Acme", "acme").fetch()
    assert item.compensation is not None
    assert item.compensation.verified is True
    assert item.compensation.min_annual == 140_000
    assert item.compensation.max_annual == 180_000
    assert item.compensation.source_url == url
    assert item.field_provenance["compensation"] == "greenhouse_official_annual_salary"


def test_ote_or_ambiguous_salary_is_not_guessed():
    for html in (
        "<p>On-target earnings (OTE): $140,000 - $180,000 USD</p>",
        "<p>Annual Salary: $140,000 - $180,000 GBP</p>",
        "<p>Annual Salary: $180,000 - $140,000 USD</p>",
        "<p>Competitive annual compensation</p>",
    ):
        assert greenhouse._official_description_compensation({"content": html}, "https://example.com") is None


def test_verified_foreign_salary_preserves_currency_and_period():
    comp = greenhouse._official_description_compensation(
        {"content": "<p>Annual Salary: £255,000 - £325,000 GBP</p>"},
        "https://job-boards.greenhouse.io/anthropic/jobs/123",
    )
    assert comp is not None
    assert comp.currency == "GBP"
    assert comp.period == "year"
    assert comp.min_annual == 255_000


def test_monthly_and_hourly_ranges_are_not_assumed_annual():
    for heading in ("Monthly Salary", "Hourly Salary", "Expected compensation"):
        html = f"<p>{heading}: $20,000 - $30,000 USD</p>"
        assert greenhouse._official_description_compensation({"content": html}, "https://example.com") is None
