from __future__ import annotations

from bazi_engine.types import BaziInput
from bazi_engine.bazi import compute_bazi, sexagenary_day_index_from_date, DAY_OFFSET

def test_day_offset_reference_examples():
    assert DAY_OFFSET == 49
    assert sexagenary_day_index_from_date(1912, 2, 18) == 0
    assert sexagenary_day_index_from_date(1949, 10, 1) == 0

def test_month_boundaries_strict_increasing():
    inp = BaziInput(
        birth_local="2024-02-10T14:30:00",
        timezone="Europe/Berlin",
        longitude_deg=13.4050,
        latitude_deg=52.52,
    )
    res = compute_bazi(inp)
    bounds = res.month_boundaries_local_dt
    assert len(bounds) == 13
    for a, b in zip(bounds, bounds[1:]):
        assert a < b
