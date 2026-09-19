from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass(slots=True)
class ParsedPage:
    title: str
    h1: str
    text: str
    links: list[str]
    jsonld: list[object]


class _Parser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []
        self.jsonld_text: list[str] = []
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._in_jsonld = False
        self._script_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(urljoin(self.base_url, values["href"] or ""))
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "script" and (values.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._script_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld_text.append("".join(self._script_buffer).strip())
            self._script_buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._script_buffer.append(data)
            return
        cleaned = data.strip()
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if self._in_title:
            self.title_parts.append(cleaned)
        if self._in_h1:
            self.h1_parts.append(cleaned)


def parse_html_page(base_url: str, html_text: str) -> ParsedPage:
    parser = _Parser(base_url)
    parser.feed(html_text)
    jsonld: list[object] = []
    for raw in parser.jsonld_text:
        if not raw:
            continue
        try:
            jsonld.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return ParsedPage(
        title=" ".join(parser.title_parts).strip(),
        h1=" ".join(parser.h1_parts).strip(),
        text=re.sub(r"\s+", " ", html.unescape(" ".join(parser.text_parts))).strip(),
        links=list(dict.fromkeys(parser.links)),
        jsonld=jsonld,
    )


def find_jobposting_nodes(values: list[object]) -> list[dict]:
    found: list[dict] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            raw_type = value.get("@type")
            types = raw_type if isinstance(raw_type, list) else [raw_type]
            if any(str(item).lower() == "jobposting" for item in types if item is not None):
                found.append(value)
            graph = value.get("@graph")
            if graph is not None:
                walk(graph)
            for key, child in value.items():
                if key != "@graph" and isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for item in values:
        walk(item)
    return found
