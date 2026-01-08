from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
import swisseph as swe
from .ephemeris import SwissEphBackend, datetime_utc_to_jd_ut

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON,
    "Lilith": swe.MEAN_APOG,
    "NorthNode": swe.MEAN_NODE,
    "TrueNorthNode": swe.TRUE_NODE
}

@dataclass
class WesternBody:
    name: str
    longitude: float
    latitude: float
    distance: float
    speed_long: float
    is_retrograde: bool
    zodiac_sign: int
    degree_in_sign: float

def compute_western_chart(
    birth_utc_dt: Any, 
    lat: float, 
    lon: float, 
    alt: float = 0.0,
    ephe_path: str = None
) -> Dict[str, Any]:
    """
    Compute basic western chart: Planets + Houses.
    Includes True Node, Retrograde status, and High-Latitude fallback.
    """
    backend = SwissEphBackend(ephe_path=ephe_path)
    if ephe_path:
        swe.set_ephe_path(ephe_path)
    
    # JD (UT)
    jd_ut = datetime_utc_to_jd_ut(birth_utc_dt)
    
    bodies = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    
    for name, pid in PLANETS.items():
        try:
            (lon_deg, lat_deg, dist, speed_lon, _, _), ret = swe.calc_ut(jd_ut, pid, flags)
            bodies[name] = {
                "longitude": lon_deg,
                "latitude": lat_deg,
                "distance": dist,
                "speed": speed_lon,
                "is_retrograde": speed_lon < 0,
                "zodiac_sign": int(lon_deg // 30),
                "degree_in_sign": lon_deg % 30
            }
        except swe.Error as e:
            bodies[name] = {"error": str(e)}

    # Houses with Fallback
    # Default: Placidus ('P')
    # Fallback 1: Porphyry ('O') - Good fallback for high latitudes
    # Fallback 2: Whole Sign ('W') - Always works
    
    house_systems = [b'P', b'O', b'W']
    cusps = None
    ascmc = None
    used_sys = None
    
    for sys_char in house_systems:
        try:
            c, a = swe.houses(jd_ut, lat, lon, sys_char)
            # Check for validity (sometimes it returns 0s without error if it fails silently)
            if c[1] == 0.0 and c[2] == 0.0:
                 continue
            cusps = c
            ascmc = a
            used_sys = sys_char.decode('utf-8')
            break
        except swe.Error:
            continue
            
    if cusps is None:
        # Should never happen with Whole Sign, but just in case
        raise RuntimeError("Failed to calculate houses with all attempted systems.")
    
    houses = {}
    # Handle different pyswisseph versions/behaviors
    # If len is 12, we assume 0-index. If 13, likely 1-index with 0=0.
    if len(cusps) == 12:
        for i in range(12):
            houses[str(i+1)] = cusps[i]
    else:
        for i in range(1, 13):
            houses[str(i)] = cusps[i]
        
    angles = {
        "Ascendant": ascmc[0],
        "MC": ascmc[1],
        "Vertex": ascmc[3] if len(ascmc) > 3 else 0.0
    }

    return {
        "jd_ut": jd_ut,
        "house_system": used_sys,
        "bodies": bodies,
        "houses": houses,
        "angles": angles
    }
