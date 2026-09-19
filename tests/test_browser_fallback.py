from scout_engine.models import OpportunityKind
from scout_engine.sources import career_page as career_page_module
from scout_engine.sources.career_page import CareerPageAdapter


def test_browser_fallback_extracts_from_actual_detail_dom(monkeypatch):
    detail_html = """
    <html>
      <head><title>Machine Learning Intern | Example AI</title></head>
      <body>
        <h1>Machine Learning Intern</h1>
        <p>Responsibilities include building Python evaluation tooling.</p>
        <p>Qualifications: internship experience with machine learning systems.</p>
      </body>
    </html>
    """

    monkeypatch.setattr(
        career_page_module,
        "fetch_rendered_html",
        lambda url: detail_html,
    )

    adapter = CareerPageAdapter("Example AI", "example.com")
    jobs = adapter._rendered_detail_jobs("https://example.com/jobs/ml-intern")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Machine Learning Intern"
    assert job.kind == OpportunityKind.INTERNSHIP
    assert job.canonical_url == "https://example.com/jobs/ml-intern"
    assert "Python evaluation tooling" in job.description
