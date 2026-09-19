from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


def _unsafe_ip(ip: str) -> bool:
    value = ipaddress.ip_address(ip)
    return any(
        (
            value.is_private,
            value.is_loopback,
            value.is_link_local,
            value.is_multicast,
            value.is_reserved,
            value.is_unspecified,
        )
    )


def validate_public_http_url(
    url: str,
    *,
    resolver: Callable[..., list[tuple]] | None = None,
) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError(f"unsupported URL scheme: {parsed.scheme or '<missing>'}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no hostname")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("credential-bearing URLs are not allowed")

    host = parsed.hostname.rstrip(".")
    if host.lower() == "localhost":
        raise UnsafeUrlError("localhost is not allowed")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _unsafe_ip(str(literal)):
            raise UnsafeUrlError(f"non-public IP is not allowed: {host}")
        return url

    lookup = resolver or socket.getaddrinfo
    try:
        resolved = {item[4][0] for item in lookup(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise UnsafeUrlError(f"hostname resolution failed: {host}") from exc
    if not resolved:
        raise UnsafeUrlError(f"hostname did not resolve: {host}")
    for ip in resolved:
        if _unsafe_ip(ip):
            raise UnsafeUrlError(f"hostname resolves to non-public IP: {host} -> {ip}")
    return url
