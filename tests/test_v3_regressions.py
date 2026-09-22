from pathlib import Path

import pytest

from scout_engine.crawl.cache import CrawlCache
from scout_engine.crawl.html import find_jobposting_nodes, parse_html_page
from scout_engine.discovery.ats_fingerprint import fingerprint_ats_url
from scout_engine.discovery.registry import load_company_registry
from scout_engine.enrich.conversion import detect_conversion_signal
from scout_engine.enrich.eligibility import extract_experience
from scout_engine.models import Compensation, Opportunity, OpportunityKind
from scout_engine.scoring import confidence_score
from scout_engine.sources import ashby as ashby_mod
from scout_engine.sources import lever as lever_mod


@pytest.mark.parametrize(
    "url,provider,identifier",
    [
        ("https://job-boards.greenhouse.io/acme/jobs/1", "greenhouse", "acme"),
        ("https://jobs.eu.lever.co/acme/1", "lever", "acme"),
        ("https://jobs.ashbyhq.com/acme/1", "ashby", "acme"),
        ("https://apply.workable.com/acme/j/1", "workable", "acme"),
        ("https://careers.smartrecruiters.com/Acme/role", "smartrecruiters", "Acme"),
    ],
)
def test_fingerprint_matrix(url, provider, identifier):
    item = fingerprint_ats_url(url)
    assert item.provider == provider
    assert item.identifier == identifier


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Top interns may receive a return offer.", "explicit"),
        ("PPO available for strong performers.", "explicit"),
        ("Opportunity for full-time employment after the internship.", "likely"),
        ("This is a 6 month learning internship.", "unknown"),
    ],
)
def test_conversion_signal_matrix(text, expected):
    assert detect_conversion_signal(text)[0] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("0–2 years experience", (0.0, 2.0)),
        ("3+ yrs in backend systems", (3.0, None)),
        ("At least 1.5 years of experience", (1.5, None)),
        ("New graduate position", (0.0, 2.0)),
    ],
)
def test_experience_matrix(text, expected):
    assert extract_experience(text) == expected


def test_jsonld_graph_and_array_are_discovered():
    values = [
        {
            "@graph": [
                {"@type": "Organization", "name": "Acme"},
                {"@type": ["Thing", "JobPosting"], "title": "Backend Intern"},
            ]
        }
    ]
    nodes = find_jobposting_nodes(values)
    assert len(nodes) == 1
    assert nodes[0]["title"] == "Backend Intern"


def test_html_parser_dedupes_links_and_reads_h1():
    page = parse_html_page(
        "https://example.com/careers",
        '<html><head><title>Jobs</title></head><body><h1>AI Intern</h1>'
        '<a href="/jobs/1">one</a><a href="/jobs/1">again</a></body></html>',
    )
    assert page.h1 == "AI Intern"
    assert page.links == ["https://example.com/jobs/1"]


def test_cache_roundtrip(tmp_path):
    cache = CrawlCache(tmp_path / "crawl.json")
    cache.put("career:example.com", {"etag": "abc", "opportunities": []})
    reloaded = CrawlCache(tmp_path / "crawl.json")
    assert reloaded.get("career:example.com")["etag"] == "abc"


def test_registry_respects_enabled_and_priority(tmp_path):
    path = tmp_path / "companies.yaml"
    path.write_text(
        "companies:\n"
        "  - name: B\n    domain: b.example\n    priority: 2\n"
        "  - name: A\n    domain: a.example\n    priority: 1\n"
        "  - name: C\n    domain: c.example\n    enabled: false\n",
        encoding="utf-8",
    )
    items = load_company_registry(str(path))
    assert [x.name for x in items] == ["A", "B"]


def test_source_trust_affects_confidence():
    kwargs = dict(
        company="Acme",
        title="AI Intern",
        kind=OpportunityKind.INTERNSHIP,
        source="career_page",
        canonical_url="https://example.com/jobs/1",
        description="Build Python systems",
        remote=True,
        last_verified_utc="2026-09-19T00:00:00+00:00",
    )
    high = Opportunity(id="a", source_confidence=0.98, **kwargs)
    low = Opportunity(id="b", source_confidence=0.65, **kwargs)
    assert confidence_score(high) > confidence_score(low)


def test_opportunity_roundtrip_preserves_v3_fields():
    original = Opportunity(
        id="x",
        company="Acme",
        title="ML Intern",
        kind=OpportunityKind.INTERNSHIP,
        source="career_page",
        canonical_url="https://example.com/x",
        application_url="https://example.com/apply/x",
        conversion_signal="explicit",
        conversion_evidence=["return offer"],
        source_status="open",
        extraction_method="jobposting_jsonld",
        field_provenance={"title": "jsonld"},
        compensation=Compensation(currency="USD", min_annual=20_000, verified=True, converted_min_annual_inr=1_800_000),
    )
    restored = Opportunity.from_dict(original.to_dict())
    assert restored.application_url.endswith("/apply/x")
    assert restored.conversion_signal == "explicit"
    assert restored.compensation.min_lpa_inr == 18


def test_lever_parses_salary_and_workplace(monkeypatch):
    monkeypatch.setattr(
        lever_mod,
        "get_json",
        lambda _: [
            {
                "id": "1",
                "text": "Backend Intern",
                "descriptionPlain": "Python backend internship",
                "categories": {"location": "Remote", "commitment": "Internship"},
                "hostedUrl": "https://jobs.lever.co/acme/1",
                "applyUrl": "https://jobs.lever.co/acme/1/apply",
                "workplaceType": "remote",
                "salaryRange": {"currency": "INR", "interval": "year", "min": 1200000, "max": 1600000},
            }
        ],
    )
    item = lever_mod.LeverAdapter("Acme", "acme").fetch()[0]
    assert item.kind == OpportunityKind.INTERNSHIP
    assert item.workplace_type == "remote"
    assert item.compensation.min_lpa_inr == 12


def test_ashby_parses_published_workplace_and_employment(monkeypatch):
    monkeypatch.setattr(
        ashby_mod,
        "get_json",
        lambda _: {
            "jobs": [
                {
                    "id": "1",
                    "title": "ML Intern",
                    "location": "Bengaluru",
                    "isRemote": False,
                    "workplaceType": "Hybrid",
                    "employmentType": "Intern",
                    "descriptionPlain": "Python ML",
                    "publishedAt": "2026-09-18T10:00:00Z",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                }
            ]
        },
    )
    item = ashby_mod.AshbyAdapter("Acme", "acme").fetch()[0]
    assert item.kind == OpportunityKind.INTERNSHIP
    assert item.workplace_type == "Hybrid"
    assert item.posted_at_utc.startswith("2026-09-18T10:00:00")


def test_heuristic_rejects_career_index_page():
    from scout_engine.crawl.html import parse_html_page
    from scout_engine.sources.career_page import _heuristic_opportunity
    page = parse_html_page(
        "https://example.com/company/careers",
        "<html><body><h1>Join Our Team</h1><p>Engineering careers and open roles. Experience great work.</p></body></html>",
    )
    assert _heuristic_opportunity("Example", "career:example.com", "https://example.com/company/careers", page) is None


def test_compact_recovery_preserves_annotations_in_metadata():
    item = Opportunity.from_dict({
        "stable_id": "amazon:1",
        "title": "Amazon — Software Engineer Intern",
        "kind": "internship",
        "stage": "qualified",
        "verified_open": "2026-09-22",
        "evidence_matches": ["python"],
    })
    assert item.metadata["verified_open"] == "2026-09-22"
    assert item.metadata["evidence_matches"] == ["python"]
