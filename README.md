# bazi_engine v0.2

Deterministic Four Pillars (Year/Month/Day/Hour) based on astronomical solar-term boundaries.

Features:

- Swiss Ephemeris (pyswisseph): Sun apparent longitude + solcross_ut
- IANA timezone input (zoneinfo) with strict DST validation option
- Optional LMT chart time (longitude/15h)
- Year boundary at LiChun (315 deg)
- Month boundaries from exact Jie crossings (315 + 30*k)
- Day pillar from JDN-based sexagenary day index
- Hour pillar from 2h branches + Zi day-boundary option
- Optional 24 solar terms computed for diagnostics/cross-validation


## Run
python -m bazi_engine.cli <LOCAL_ISO_DATE> [OPTIONS]

Example:
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52

Options:
  --tz TIMEZONE         Timezone name (default: Europe/Berlin)
  --lon DEGREES         Longitude (default: 13.4050)
  --lat DEGREES         Latitude (default: 52.52)
  --standard {CIVIL,LMT} Time standard (default: CIVIL)
  --boundary {midnight,zi} Day boundary (default: midnight)
  --json                Output JSON format

## Tests
pytest -q
