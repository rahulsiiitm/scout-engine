from types import SimpleNamespace

import pytest

from scout_engine.crawl.client import FetchResult
from scout_engine.models import Opportunity, OpportunityKind
from scout_engine.sources import career_page
from scout_engine.sources.base import SourceError


INDEX_URL = "https://example.com/company/careers/all-jobs"
DETAIL_URL = "https://example.com/company/careers/jobs/123"


class FakeCache:
    saved = None

    def __init__(self):
        self.saved = None

    def get(self, key):
        return {"etag": None, "last_modified": None, "opportunities": []}

    def put(self, key, value):
        self.saved = value
        type(self).saved = value


class FakeClient:
    calls = []
    responses = []

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def fetch_text(self, url, *, etag=None, last_modified=None):
        self.calls.append((url, etag, last_modified))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _adapter(monkeypatch):
    monkeypatch.setattr(career_page, "CrawlClient", FakeClient)
    monkeypatch.setattr(career_page, "CrawlCache", FakeCache)
    adapter = career_page.CareerPageAdapter(
        "Example", "example.com", careers_url=INDEX_URL, browser_fallback=False
    )
    policy = SimpleNamespace(
        can_fetch=lambda user_agent, url: True,
        crawl_delay=lambda user_agent: None,
    )
    monkeypatch.setattr(adapter, "_robots", lambda *args: policy)
    monkeypatch.setattr(
        adapter, "_sitemap_urls", lambda *args: [DETAIL_URL]
    )
    FakeClient.calls = []
    FakeClient.responses = []
    FakeCache.saved = None
    return adapter


def test_oversized_career_index_uses_robots_permitted_sitemap(monkeypatch):
    adapter = _adapter(monkeypatch)
    job = Opportunity(
        id="career:example.com:123",
        company="Example",
        title="Machine Learning Intern",
        kind=OpportunityKind.INTERNSHIP,
        source="career_page",
        canonical_url=DETAIL_URL,
    )
    monkeypatch.setattr(
        adapter,
        "_process_page",
        lambda *args: ([job], SimpleNamespace(links=[])),
    )
    FakeClient.responses = [
        RuntimeError("response exceeded 2000000 bytes"),
        FetchResult(url=DETAIL_URL, status_code=200, text="<html>job</html>"),
    ]

    jobs = adapter.fetch()

    assert [item.id for item in jobs] == [job.id]
    assert FakeClient.calls == [
        (INDEX_URL, None, None),
        (DETAIL_URL, None, None),
    ]
    assert FakeCache.saved["etag"] is None
    assert FakeCache.saved["opportunities"][0]["id"] == job.id


def test_oversized_index_without_permitted_sitemap_jobs_fails_closed(monkeypatch):
    adapter = _adapter(monkeypatch)
    monkeypatch.setattr(adapter, "_sitemap_urls", lambda *args: [])
    FakeClient.responses = [RuntimeError("response too large: 2100000 bytes")]

    with pytest.raises(SourceError, match="no robots-permitted sitemap job URLs"):
        adapter.fetch()

    assert FakeClient.calls == [(INDEX_URL, None, None)]
    assert FakeCache.saved is None


def test_non_size_fetch_errors_do_not_trigger_sitemap_fallback(monkeypatch):
    adapter = _adapter(monkeypatch)
    FakeClient.responses = [RuntimeError("connection reset")]

    with pytest.raises(RuntimeError, match="connection reset"):
        adapter.fetch()

    assert FakeClient.calls == [(INDEX_URL, None, None)]
    assert FakeCache.saved is None


def test_sitemap_discovery_skips_cross_host_root_map(monkeypatch):
    adapter = _adapter(monkeypatch)
    policy = SimpleNamespace(
        site_maps=lambda: ["https://cdn.example.net/sitemap.xml"],
        can_fetch=lambda user_agent, url: True,
    )
    client = FakeClient()

    assert adapter._sitemap_urls(client, policy, INDEX_URL) == []
    assert FakeClient.calls == []


def test_sitemap_discovery_skips_cross_host_nested_map(monkeypatch):
    adapter = _adapter(monkeypatch)
    policy = SimpleNamespace(
        site_maps=lambda: ["https://example.com/sitemap.xml"],
        can_fetch=lambda user_agent, url: True,
    )
    client = FakeClient()
    FakeClient.calls = []
    FakeClient.responses = [
        FetchResult(url="https://example.com/sitemap.xml", status_code=200, text="<sitemap/>")
    ]
    monkeypatch.setattr(
        career_page,
        "parse_sitemap",
        lambda text: SimpleNamespace(
            nested_sitemaps=[SimpleNamespace(url="https://cdn.example.net/sitemap-jobs.xml")],
            urls=[],
        ),
    )

    assert adapter._sitemap_urls(client, policy, INDEX_URL) == []
    assert FakeClient.calls == [("https://example.com/sitemap.xml", None, None)]
