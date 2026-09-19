from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    url: str
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedSitemap:
    urls: list[SitemapEntry]
    nested_sitemaps: list[SitemapEntry]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(xml_text: str) -> ParsedSitemap:
    root = ElementTree.fromstring(xml_text)
    urls: list[SitemapEntry] = []
    nested: list[SitemapEntry] = []
    root_name = _local(root.tag)
    for child in root:
        loc = None
        lastmod = None
        for node in child:
            name = _local(node.tag)
            if name == "loc":
                loc = (node.text or "").strip()
            elif name == "lastmod":
                lastmod = (node.text or "").strip() or None
        if not loc:
            continue
        item = SitemapEntry(loc, lastmod)
        if root_name == "sitemapindex":
            nested.append(item)
        else:
            urls.append(item)
    return ParsedSitemap(urls=urls, nested_sitemaps=nested)
