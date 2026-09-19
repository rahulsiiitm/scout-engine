from scout_engine.crawl.html import parse_html_page
from scout_engine.crawl.jsonld import opportunities_from_jsonld


def test_jobposting_jsonld_is_normalized_with_provenance():
    html = '''
    <html><head>
    <script type="application/ld+json">
    {
      "@context":"https://schema.org",
      "@type":"JobPosting",
      "title":"Machine Learning Intern",
      "description":"Build Python ML systems. Successful interns may receive a full-time offer.",
      "datePosted":"2026-09-18T00:00:00+00:00",
      "validThrough":"2026-10-15T23:59:00+00:00",
      "employmentType":"INTERN",
      "hiringOrganization":{"name":"Example AI"},
      "jobLocation":{"address":{"addressLocality":"Bengaluru","addressCountry":"IN"}},
      "baseSalary":{"currency":"INR","value":{"minValue":1200000,"maxValue":1800000,"unitText":"YEAR"}},
      "url":"https://example.ai/jobs/ml-intern"
    }
    </script></head><body><h1>Machine Learning Intern</h1></body></html>
    '''
    page = parse_html_page("https://example.ai/careers", html)
    jobs = opportunities_from_jsonld(page.jsonld, company="Example AI", page_url="https://example.ai/careers", source_key="career:example.ai")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.kind.value == "internship"
    assert job.location == "Bengaluru, IN"
    assert job.compensation.min_lpa_inr == 12
    assert job.field_provenance["compensation"] == "jobposting_jsonld"
    assert job.source_confidence == 0.95
