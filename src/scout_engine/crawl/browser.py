from __future__ import annotations

from urllib.parse import urlsplit

from .security import UnsafeUrlError, validate_public_http_url


def fetch_rendered_html(url: str, *, timeout_ms: int = 20_000, max_html_bytes: int = 2_000_000) -> str:
    validate_public_http_url(url)
    try:
        from playwright.sync_api import Route, sync_playwright
    except ImportError as exc:
        raise RuntimeError("browser fallback requires `pip install scout-engine[browser]`") from exc

    host_cache: dict[str, bool] = {}

    def guard(route: Route) -> None:
        request_url = route.request.url
        parsed = urlsplit(request_url)
        host = (parsed.hostname or "").lower()
        if host in host_cache:
            route.continue_() if host_cache[host] else route.abort()
            return
        try:
            validate_public_http_url(request_url)
            host_cache[host] = True
            route.continue_()
        except UnsafeUrlError:
            host_cache[host] = False
            route.abort()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.route("**/*", guard)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1200)
            content = page.content()
            if len(content.encode("utf-8")) > max_html_bytes:
                raise RuntimeError("rendered page exceeded size limit")
            return content
        finally:
            browser.close()
