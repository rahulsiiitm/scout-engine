from scout_engine.dedupe import duplicate_similarity
from scout_engine.models import Opportunity, OpportunityKind


def make(id_, title, url, location="Bengaluru"):
    return Opportunity(id=id_,company="Example AI",title=title,kind=OpportunityKind.INTERNSHIP,source="test",canonical_url=url,location=location)


def test_same_url_is_exact_duplicate_even_with_tracking_query():
    a = make("a", "AI Engineer Intern", "https://example.com/jobs/123?utm_source=x")
    b = make("b", "AI Engineer Internship", "https://example.com/jobs/123")
    assert duplicate_similarity(a, b) == 1.0


def test_company_title_similarity_detects_cross_source_duplicate():
    a = make("a", "Machine Learning Engineer Intern", "https://a.example/1")
    b = make("b", "ML Engineer Intern", "https://b.example/2")
    assert duplicate_similarity(a, b) >= 0.70
