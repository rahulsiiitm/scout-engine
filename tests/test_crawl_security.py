import socket

import pytest

from scout_engine.crawl.security import UnsafeUrlError, validate_public_http_url


def fake_public(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


def fake_private(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))]


def test_blocks_non_http_and_private_addresses():
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("file:///etc/passwd")
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("http://127.0.0.1/internal")
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("https://example.com", resolver=fake_private)


def test_allows_public_http_host():
    assert validate_public_http_url("https://example.com/jobs", resolver=fake_public).startswith("https://")
