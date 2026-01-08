from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Tuple

class LocalTimeError(ValueError):
    pass

def parse_local_iso(birth_local_iso: str, tz_name: str, *, strict: bool, fold: int) -> datetime:
    naive = datetime.fromisoformat(birth_local_iso)
    tz = ZoneInfo(tz_name)
    dt = naive.replace(tzinfo=tz, fold=fold)

    if not strict:
        return dt

    # Round-trip check local -> utc -> local
    utc = dt.astimezone(timezone.utc)
    back = utc.astimezone(tz)

    if back.replace(tzinfo=None) != naive:
        raise LocalTimeError(
            f"Nonexistent or normalized local time for zone {tz_name}: {birth_local_iso}. "
            f"Round-trip became {back.isoformat()} (fold={back.fold})."
        )
    return dt

def lmt_tzinfo(longitude_deg: float) -> timezone:
    return timezone(timedelta(seconds=longitude_deg * 240.0))

def to_chart_local(birth_local: datetime, longitude_deg: float, time_standard: str) -> Tuple[datetime, datetime]:
    birth_utc = birth_local.astimezone(timezone.utc)
    if time_standard.upper() == "LMT":
        return birth_utc.astimezone(lmt_tzinfo(longitude_deg)), birth_utc
    return birth_local, birth_utc

def apply_day_boundary(dt_local: datetime, day_boundary: str) -> datetime:
    if day_boundary.lower() == "zi":
        return dt_local + timedelta(hours=1)
    return dt_local
