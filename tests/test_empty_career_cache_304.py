"""A conditional 304 must not trap an empty career extraction cache forever."""
from types import SimpleNamespace

import pytest

from scout_engine.crawl.client import FetchResult
from scout_engine.models import Opportunity, OpportunityKind
from scout_engine.sources import career_page
from scout_engine.sources.base import SourceError


URL = "https://example.com/careers"


class FakeCache:
    saved = None

    def __init__(self):
        pass

    def get(self, key):
        return {"etag": '"v1"', "last_modified": None, "opportunities": []}

    def put(self, key, value):
        self.saved = value


class FakeClient:
    responses = []
    calls = []

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def fetch_text(self, url, *, etag=None, last_modified=None):
        self.calls.append((url, etag, last_modified))
        return self.responses.pop(0)


def _adapter(monkeypatch):
    monkeypatch.setattr(career_page, "CrawlClient", FakeClient)
    monkeypatch.setattr(career_page, "CrawlCache", FakeCache)
    adapter = career_page.CareerPageAdapter(
        "Example", "example.com", careers_url=URL, browser_fallback=False
    )
    policy = SimpleNamespace(can_fetch=lambda *args: True, crawl_delay=lambda *args: None)
    monkeypatch.setattr(adapter, "_robots", lambda *args: policy)
    monkeypatch.setattr(adapter, "_sitemap_urls", lambda *args: [])
    FakeClient.calls = []
    return adapter


def test_empty_cache_304_retries_without_conditional_headers(monkeypatch):
    adapter = _adapter(monkeypatch)
    job = Opportunity(
        id="career:example:1",
        company="Example",
        title="Software Engineer",
        kind=OpportunityKind.FULL_TIME,
        source="career_page",
        canonical_url="https://example.com/jobs/1",
    )
    monkeypatch.setattr(
        adapter,
        "_process_page",
        lambda *args: ([job], SimpleNamespace(links=[])),
    )
    FakeClient.responses = [
        FetchResult(url=URL, status_code=304, text="", not_modified=True),
        FetchResult(url=URL, status_code=200, text="<html>jobs</html>"),
    ]
    result = adapter.fetch()
    assert len(result) == 1
    assert result[0].id == job.id
    assert FakeClient.calls == [(URL, '"v1"', None), (URL, None, None)]


def test_empty_cache_repeated_304_fails_closed(monkeypatch):
    adapter = _adapter(monkeypatch)
    FakeClient.responses = [
        FetchResult(url=URL, status_code=304, text="", not_modified=True),
        FetchResult(url=URL, status_code=304, text="", not_modified=True),
    ]
    with pytest.raises(SourceError, match="unexpected HTTP 304"):
        adapter.fetch()
    assert FakeClient.calls == [(URL, '"v1"', None), (URL, None, None)]
