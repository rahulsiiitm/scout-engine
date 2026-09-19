from scout_engine.enrich.fx import FxTable, _parse_ecb
from scout_engine.models import Compensation


def test_ecb_cross_conversion_to_inr():
    table = FxTable("2026-09-18", {"USD": 1.20, "INR": 108.0})
    value, rate = table.to_inr(100_000, "USD")
    assert value == 9_000_000
    assert rate == 90.0


def test_ecb_parser():
    xml = '<Envelope><Cube><Cube time="2026-09-18"><Cube currency="USD" rate="1.20"/><Cube currency="INR" rate="108.0"/></Cube></Cube></Envelope>'
    table = _parse_ecb(xml)
    assert table.date == "2026-09-18"
    assert table.rates_per_eur["INR"] == 108.0


def test_foreign_compensation_uses_converted_floor():
    comp = Compensation(currency="USD", min_annual=20_000, verified=True, converted_min_annual_inr=1_800_000)
    assert comp.min_lpa_inr == 18
