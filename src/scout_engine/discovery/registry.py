from __future__ import annotations

from dataclasses import dataclass

from ..config import load_yaml


@dataclass(frozen=True, slots=True)
class CompanySource:
    name: str
    domain: str
    careers_url: str | None = None
    mode: str = "auto"
    priority: int = 2
    enabled: bool = True
    max_pages: int | None = None


def load_company_registry(path: str = "config/companies.yaml") -> list[CompanySource]:
    raw = load_yaml(path)
    out: list[CompanySource] = []
    for item in raw.get("companies", []) or []:
        if not item.get("enabled", True):
            continue
        out.append(
            CompanySource(
                name=item["name"],
                domain=item["domain"],
                careers_url=item.get("careers_url"),
                mode=item.get("mode", "auto"),
                priority=int(item.get("priority", 2)),
                enabled=True,
                max_pages=int(item["max_pages"]) if item.get("max_pages") is not None else None,
            )
        )
    return sorted(out, key=lambda x: (x.priority, x.name.lower()))
