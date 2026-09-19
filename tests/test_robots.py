from scout_engine.crawl.robots import RobotsPolicy


def test_robots_obeys_disallow_and_sitemap():
    policy = RobotsPolicy.from_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="User-agent: *\nDisallow: /private\nSitemap: https://example.com/sitemap.xml\n",
    )
    assert policy.can_fetch("ScoutEngineBot/1.0", "https://example.com/careers")
    assert not policy.can_fetch("ScoutEngineBot/1.0", "https://example.com/private/job")
    assert policy.site_maps() == ["https://example.com/sitemap.xml"]


def test_robots_404_allows_but_5xx_fails_closed():
    missing = RobotsPolicy.from_response(url="https://x/robots.txt", status_code=404, text="")
    broken = RobotsPolicy.from_response(url="https://x/robots.txt", status_code=503, text="")
    assert missing.can_fetch("*", "https://x/jobs")
    assert not broken.can_fetch("*", "https://x/jobs")
