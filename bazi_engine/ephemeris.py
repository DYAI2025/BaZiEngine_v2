from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

import swisseph as swe

def norm360(deg: float) -> float:
    x = deg % 360.0
    if x < 0:
        x += 360.0
    return x

def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0

class EphemerisBackend(Protocol):
    def delta_t_seconds(self, jd_ut: float) -> float: ...
    def jd_tt_from_jd_ut(self, jd_ut: float) -> float: ...
    def sun_lon_deg_ut(self, jd_ut: float) -> float: ...
    def solcross_ut(self, target_lon_deg: float, jd_start_ut: float) -> Optional[float]: ...

@dataclass(frozen=True)
class SwissEphBackend:
    flags: int = swe.FLG_SWIEPH
    ephe_path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.ephe_path:
            swe.set_ephe_path(self.ephe_path)

    def delta_t_seconds(self, jd_ut: float) -> float:
        return swe.deltat(jd_ut) * 86400.0

    def jd_tt_from_jd_ut(self, jd_ut: float) -> float:
        return jd_ut + swe.deltat(jd_ut)

    def sun_lon_deg_ut(self, jd_ut: float) -> float:
        (lon, _lat, _dist, *_), _ret = swe.calc_ut(jd_ut, swe.SUN, self.flags)
        return norm360(lon)

    def solcross_ut(self, target_lon_deg: float, jd_start_ut: float) -> Optional[float]:
        return swe.solcross_ut(target_lon_deg, jd_start_ut, self.flags)

def datetime_utc_to_jd_ut(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None or dt_utc.utcoffset() != timedelta(0):
        raise ValueError("Expected aware UTC datetime")
    h = dt_utc.hour + dt_utc.minute / 60.0 + (dt_utc.second + dt_utc.microsecond / 1e6) / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)

def jd_ut_to_datetime_utc(jd_ut: float) -> datetime:
    y, m, d, h = swe.revjul(jd_ut)
    hour = int(h)
    rem = (h - hour) * 3600.0
    minute = int(rem // 60.0)
    sec = rem - minute * 60.0
    second = int(sec)
    micro = int(round((sec - second) * 1_000_000))
    if micro >= 1_000_000:
        micro -= 1_000_000
        second += 1
    if second >= 60:
        second -= 60
        minute += 1
    if minute >= 60:
        minute -= 60
        hour += 1
    base = datetime(y, m, d, 0, 0, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(hours=hour, minutes=minute, seconds=second, microseconds=micro)
