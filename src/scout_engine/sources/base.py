from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..models import Opportunity


class SourceError(RuntimeError):
    pass


def get_json(url: str, timeout: int = 30) -> Any:
    try:
        response = httpx.get(
            url,
            timeout=float(timeout),
            headers={"User-Agent": "scout-engine/0.3 (+https://github.com/rahulsiiitm/scout-engine)"},
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise SourceError(f"failed to fetch {url}: {exc}") from exc


class SourceAdapter(ABC):
    source_name: str

    @property
    def source_key(self) -> str:
        return self.source_name

    def effective_source_keys(self) -> set[str]:
        return {self.source_key}

    @abstractmethod
    def fetch(self) -> list[Opportunity]:
        raise NotImplementedError
