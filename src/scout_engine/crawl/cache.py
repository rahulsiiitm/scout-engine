from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CrawlCache:
    def __init__(self, path: str | Path = "data/crawl-cache.json") -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = {"version": 1, "entries": {}}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data = loaded
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str) -> dict[str, Any]:
        return dict(self.data.get("entries", {}).get(key, {}) or {})

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.data.setdefault("entries", {})[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
