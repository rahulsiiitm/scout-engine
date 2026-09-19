from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from ..models import Opportunity


class SourceError(RuntimeError):
    pass


def get_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "scout-engine/0.2 (+https://github.com/rahulsiiitm/scout-engine)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise SourceError(f"failed to fetch {url}: {exc}") from exc


class SourceAdapter(ABC):
    source_name: str

    @abstractmethod
    def fetch(self) -> list[Opportunity]:
        raise NotImplementedError
