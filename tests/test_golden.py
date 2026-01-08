from __future__ import annotations

import pytest

from bazi_engine.types import BaziInput
from bazi_engine.bazi import compute_bazi

GOLDEN_CASES = [
    (
        "Berlin_2024-02-10",
        BaziInput(
            birth_local="2024-02-10T14:30:00",
            timezone="Europe/Berlin",
            longitude_deg=13.4050,
            latitude_deg=52.52,
        ),
        ("JiaChen", "BingYin", "JiaChen", "XinWei"),
    ),
    (
        "Berlin_just_before_LiChun",
        BaziInput(
            birth_local="2024-02-04T09:26:00",
            timezone="Europe/Berlin",
            longitude_deg=13.4050,
            latitude_deg=52.52,
        ),
        ("GuiMao", "YiChou", "WuXu", "DingSi"),
    ),
    (
        "Berlin_just_after_LiChun",
        BaziInput(
            birth_local="2024-02-04T09:28:00",
            timezone="Europe/Berlin",
            longitude_deg=13.4050,
            latitude_deg=52.52,
        ),
        ("JiaChen", "BingYin", "WuXu", "DingSi"),
    ),
    (
        "Madrid_zi_LMT",
        BaziInput(
            birth_local="2024-02-04T23:30:00",
            timezone="Europe/Madrid",
            longitude_deg=-3.7038,
            latitude_deg=40.4168,
            time_standard="LMT",
            day_boundary="zi",
        ),
        ("JiaChen", "BingYin", "WuXu", "GuiHai"),
    ),
]

@pytest.mark.parametrize("name, inp, exp", GOLDEN_CASES, ids=[c[0] for c in GOLDEN_CASES])
def test_golden(name, inp, exp):
    res = compute_bazi(inp)
    got = (str(res.pillars.year), str(res.pillars.month), str(res.pillars.day), str(res.pillars.hour))
    assert got == exp
