from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import httpx

from ..models import Compensation


ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


@dataclass(frozen=True, slots=True)
class FxTable:
    date: str
    rates_per_eur: dict[str, float]

    def to_inr(self, amount: float, currency: str) -> tuple[float, float]:
        source = currency.upper()
        rates = dict(self.rates_per_eur)
        rates["EUR"] = 1.0
        if source not in rates or "INR" not in rates:
            raise KeyError(source)
        inr_per_source = rates["INR"] / rates[source]
        return amount * inr_per_source, inr_per_source


def _parse_ecb(xml_text: str) -> FxTable:
    root = ElementTree.fromstring(xml_text)
    date = ""
    rates: dict[str, float] = {}
    for node in root.iter():
        if "time" in node.attrib:
            date = node.attrib["time"]
        currency = node.attrib.get("currency")
        rate = node.attrib.get("rate")
        if currency and rate:
            rates[currency.upper()] = float(rate)
    if not date or "INR" not in rates:
        raise ValueError("ECB response missing date or INR rate")
    return FxTable(date=date, rates_per_eur=rates)


def load_fx_table(path: str | Path = "data/fx-rates.json") -> FxTable | None:
    file = Path(path)
    if not file.exists():
        return None
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
        return FxTable(str(raw["date"]), {k: float(v) for k, v in raw["rates_per_eur"].items()})
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def fetch_fx_table(path: str | Path = "data/fx-rates.json") -> FxTable:
    response = httpx.get(ECB_URL, timeout=15.0, headers={"User-Agent": "scout-engine/0.3"})
    response.raise_for_status()
    table = _parse_ecb(response.text)
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps({"version": 1, "date": table.date, "rates_per_eur": table.rates_per_eur}, indent=2) + "\n",
        encoding="utf-8",
    )
    return table


_FX_TABLE: FxTable | None = None


def current_fx_table() -> FxTable:
    global _FX_TABLE
    if _FX_TABLE is not None:
        return _FX_TABLE
    cached = load_fx_table()
    if cached:
        try:
            age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(cached.date).date()).days
        except ValueError:
            age = 999
        if age <= 7:
            _FX_TABLE = cached
            return cached
    _FX_TABLE = fetch_fx_table()
    return _FX_TABLE


def convert_compensation_to_inr(compensation: Compensation) -> Compensation:
    if compensation.currency.upper() == "INR" or compensation.min_annual is None:
        return compensation
    try:
        table = current_fx_table()
        converted_min, rate = table.to_inr(float(compensation.min_annual), compensation.currency)
        converted_max = None
        if compensation.max_annual is not None:
            converted_max, _ = table.to_inr(float(compensation.max_annual), compensation.currency)
    except Exception:
        return compensation
    compensation.converted_min_annual_inr = converted_min
    compensation.converted_max_annual_inr = converted_max
    compensation.fx_rate = rate
    compensation.fx_rate_date = table.date
    compensation.fx_source = ECB_URL
    return compensation
