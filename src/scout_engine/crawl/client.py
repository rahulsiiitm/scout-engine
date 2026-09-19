from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from .security import validate_public_http_url


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    status_code: int
    text: str
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


class CrawlClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_redirects: int = 5,
        max_response_bytes: int = 2_000_000,
        user_agent: str = "ScoutEngineBot/1.0 (+https://github.com/rahulsiiitm/scout-engine)",
    ) -> None:
        self.max_redirects = max_redirects
        self.max_response_bytes = max_response_bytes
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"},
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "CrawlClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch_text(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        current = validate_public_http_url(url)
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        for _ in range(self.max_redirects + 1):
            with self.client.stream("GET", current, headers=headers) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise RuntimeError(f"redirect without Location while fetching {current}")
                    current = validate_public_http_url(urljoin(current, location))
                    headers = {}
                    continue

                if response.status_code == 304:
                    return FetchResult(
                        url=str(response.url),
                        status_code=304,
                        text="",
                        etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"),
                        not_modified=True,
                    )

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_response_bytes:
                    raise RuntimeError(f"response too large: {content_length} bytes")

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > self.max_response_bytes:
                        raise RuntimeError(f"response exceeded {self.max_response_bytes} bytes")
                encoding = response.encoding or "utf-8"
                text = bytes(body).decode(encoding, errors="replace")
                return FetchResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    text=text,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
        raise RuntimeError(f"too many redirects while fetching {url}")
