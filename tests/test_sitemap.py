from scout_engine.crawl.sitemap import parse_sitemap


def test_urlset_and_lastmod():
    parsed = parse_sitemap(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>https://example.com/jobs/1</loc><lastmod>2026-09-18</lastmod></url>'
        '</urlset>'
    )
    assert parsed.urls[0].url.endswith("/jobs/1")
    assert parsed.urls[0].last_modified == "2026-09-18"


def test_sitemap_index():
    parsed = parse_sitemap(
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<sitemap><loc>https://example.com/jobs.xml</loc></sitemap>'
        '</sitemapindex>'
    )
    assert parsed.nested_sitemaps[0].url.endswith("jobs.xml")
