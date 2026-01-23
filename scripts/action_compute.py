from __future__ import annotations

import argparse
import json
from datetime import timezone
from pathlib import Path

from bazi_engine.bazi import compute_bazi
from bazi_engine.ephemeris import ensure_ephemeris_files
from bazi_engine.time_utils import parse_local_iso
from bazi_engine.types import BaziInput
from bazi_engine.western import compute_western_chart


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BaZi + ephemeris calculations for GitHub Actions.")
    parser.add_argument("--date", required=True, help="ISO 8601 local datetime, e.g. 2024-02-10T14:30:00")
    parser.add_argument("--tz", default="Europe/Berlin", help="Timezone name (default: Europe/Berlin)")
    parser.add_argument("--lon", type=float, default=13.4050, help="Longitude in degrees")
    parser.add_argument("--lat", type=float, default=52.52, help="Latitude in degrees")
    parser.add_argument("--standard", choices=["CIVIL", "LMT"], default="CIVIL")
    parser.add_argument("--boundary", choices=["midnight", "zi"], default="midnight")
    parser.add_argument("--strict", dest="strict", action="store_true", default=True)
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    parser.add_argument("--ephe-path", default=None, help="Optional Swiss Ephemeris path override")
    parser.add_argument("--output", default="action_result.json", help="Output JSON file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_ephemeris_files(args.ephe_path)

    bazi_input = BaziInput(
        birth_local=args.date,
        timezone=args.tz,
        longitude_deg=args.lon,
        latitude_deg=args.lat,
        time_standard=args.standard,
        day_boundary=args.boundary,
        strict_local_time=args.strict,
        fold=0,
    )
    bazi_result = compute_bazi(bazi_input)

    dt_local = parse_local_iso(args.date, args.tz, strict=args.strict, fold=0)
    dt_utc = dt_local.astimezone(timezone.utc)
    western_chart = compute_western_chart(dt_utc, args.lat, args.lon)

    payload = {
        "input": {
            "date": args.date,
            "tz": args.tz,
            "lon": args.lon,
            "lat": args.lat,
            "standard": args.standard,
            "boundary": args.boundary,
            "strict": args.strict,
        },
        "bazi": {
            "pillars": {
                "year": str(bazi_result.pillars.year),
                "month": str(bazi_result.pillars.month),
                "day": str(bazi_result.pillars.day),
                "hour": str(bazi_result.pillars.hour),
            },
            "dates": {
                "birth_local": bazi_result.birth_local_dt.isoformat(),
                "birth_utc": bazi_result.birth_utc_dt.isoformat(),
                "lichun_local": bazi_result.lichun_local_dt.isoformat(),
            },
            "solar_terms_count": (
                len(bazi_result.solar_terms_local_dt) if bazi_result.solar_terms_local_dt else 0
            ),
        },
        "western": western_chart,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
