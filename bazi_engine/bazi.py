from __future__ import annotations

from datetime import datetime

import swisseph as swe

from .types import BaziInput, BaziResult, Pillar, FourPillars, SolarTerm
from .time_utils import parse_local_iso, to_chart_local, apply_day_boundary
from .ephemeris import SwissEphBackend, datetime_utc_to_jd_ut, jd_ut_to_datetime_utc
from .jieqi import compute_month_boundaries_from_lichun, compute_24_solar_terms_for_window

from .constants import STEMS, BRANCHES, DAY_OFFSET

def jdn_gregorian(y: int, m: int, d: int) -> int:
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045

def sexagenary_day_index_from_date(y: int, m: int, d: int, offset: int = DAY_OFFSET) -> int:
    return (jdn_gregorian(y, m, d) + offset) % 60

def pillar_from_index60(idx60: int) -> Pillar:
    return Pillar(idx60 % 10, idx60 % 12)

def year_pillar_from_solar_year(solar_year: int) -> Pillar:
    idx60 = (solar_year - 1984) % 60
    return pillar_from_index60(idx60)

def month_pillar_from_year_stem(year_stem_index: int, month_index: int) -> Pillar:
    branch_index = (2 + month_index) % 12
    stem_index = (year_stem_index * 2 + 2 + month_index) % 10
    return Pillar(stem_index, branch_index)

def hour_branch_index(dt_local: datetime) -> int:
    return ((dt_local.hour + 1) // 2) % 12

def hour_pillar_from_day_stem(day_stem_index: int, hour_branch: int) -> Pillar:
    stem_index = (day_stem_index * 2 + hour_branch) % 10
    return Pillar(stem_index, hour_branch)

def _lichun_jd_ut_for_year(year: int, backend: SwissEphBackend) -> float:
    jd0 = swe.julday(year, 1, 1, 0.0)
    return float(backend.solcross_ut(315.0, jd0))

def compute_bazi(inp: BaziInput) -> BaziResult:
    if inp.ephemeris_backend.lower() != "swisseph":
        raise NotImplementedError("v0.2 ships a skyfield stub only; swisseph is implemented.")

    backend = SwissEphBackend(ephe_path=inp.ephe_path)

    birth_local_dt = parse_local_iso(
        inp.birth_local,
        inp.timezone,
        strict=inp.strict_local_time,
        fold=int(inp.fold),
    )
    chart_local_dt, birth_utc_dt = to_chart_local(birth_local_dt, inp.longitude_deg, inp.time_standard)

    jd_ut = datetime_utc_to_jd_ut(birth_utc_dt)
    delta_t_seconds = backend.delta_t_seconds(jd_ut)
    jd_tt = backend.jd_tt_from_jd_ut(jd_ut)

    # Year by LiChun
    y = chart_local_dt.year
    jd_lichun_this = _lichun_jd_ut_for_year(y, backend)
    lichun_this_local = jd_ut_to_datetime_utc(jd_lichun_this).astimezone(chart_local_dt.tzinfo)

    if chart_local_dt < lichun_this_local:
        solar_year = y - 1
        jd_lichun_used = _lichun_jd_ut_for_year(y - 1, backend)
    else:
        solar_year = y
        jd_lichun_used = jd_lichun_this

    year_p = year_pillar_from_solar_year(solar_year)

    # Month boundaries
    month_bounds_ut = compute_month_boundaries_from_lichun(
        backend,
        jd_lichun_used,
        accuracy_seconds=inp.accuracy_seconds,
    )
    month_bounds_local = [jd_ut_to_datetime_utc(jd).astimezone(chart_local_dt.tzinfo) for jd in month_bounds_ut]

    month_index = 11
    for k in range(12):
        if month_bounds_local[k] <= chart_local_dt < month_bounds_local[k + 1]:
            month_index = k
            break
    month_p = month_pillar_from_year_stem(year_p.stem_index, month_index)

    # Day pillar
    # v0.4 Configurable Day Anchor
    if inp.day_anchor_date_iso and inp.day_anchor_pillar_idx is not None:
        anchor_dt = datetime.fromisoformat(inp.day_anchor_date_iso)
        anchor_jdn = jdn_gregorian(anchor_dt.year, anchor_dt.month, anchor_dt.day)
        # We need offset such that: (anchor_jdn + offset) % 60 == anchor_pillar_idx
        # offset = (anchor_pillar_idx - anchor_jdn) % 60
        # Python's modulo operator handles negative numbers correctly for this purpose
        calculated_offset = (inp.day_anchor_pillar_idx - anchor_jdn) % 60
    else:
        calculated_offset = DAY_OFFSET

    dt_for_day = apply_day_boundary(chart_local_dt, inp.day_boundary)
    day_idx60 = sexagenary_day_index_from_date(dt_for_day.year, dt_for_day.month, dt_for_day.day, offset=calculated_offset)
    day_p = pillar_from_index60(day_idx60)

    # Hour pillar
    hb = hour_branch_index(chart_local_dt)
    hour_p = hour_pillar_from_day_stem(day_p.stem_index, hb)

    pillars = FourPillars(year=year_p, month=month_p, day=day_p, hour=hour_p)

    # Diagnostics: 24 terms in LiChun->next LiChun window
    solar_terms = None
    try:
        term_pairs = compute_24_solar_terms_for_window(
            backend,
            month_bounds_ut[0],
            month_bounds_ut[-1],
            accuracy_seconds=inp.accuracy_seconds,
        )
        solar_terms = [
            SolarTerm(
                index=idx,
                target_lon_deg=15.0 * idx,
                utc_dt=jd_ut_to_datetime_utc(jd),
                local_dt=jd_ut_to_datetime_utc(jd).astimezone(chart_local_dt.tzinfo),
            )
            for (idx, jd) in term_pairs
        ]
    except Exception:
        solar_terms = None

    return BaziResult(
        input=inp,
        pillars=pillars,
        birth_local_dt=birth_local_dt,
        birth_utc_dt=birth_utc_dt,
        chart_local_dt=chart_local_dt,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        delta_t_seconds=delta_t_seconds,
        lichun_local_dt=jd_ut_to_datetime_utc(jd_lichun_used).astimezone(chart_local_dt.tzinfo),
        month_boundaries_local_dt=month_bounds_local,
        month_index=month_index,
        solar_terms_local_dt=solar_terms,
    )
