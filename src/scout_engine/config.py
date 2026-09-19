from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_profile(path: str | Path = "config/profile.yaml") -> dict[str, Any]:
    data = load_yaml(path)
    return data


def load_labels(path: str | Path = "config/labels.yml") -> list[dict[str, str]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError("labels config must be a list")
    return data
