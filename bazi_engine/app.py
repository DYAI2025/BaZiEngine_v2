from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from .types import BaziInput, Pillar
from .constants import STEMS, BRANCHES, ANIMALS
from .bazi import compute_bazi
from .western import compute_western_chart
from .time_utils import parse_local_iso
from .ephemeris import ensure_ephemeris_files

app = FastAPI(
    title="BaZi Engine v2 API",
    description="API for BaZi (Chinese Astrology) and Basic Western Astrology calculations.",
    version="0.2.0"
)

ZODIAC_SIGNS_DE = [
    "Widder",
    "Stier",
    "Zwillinge",
    "Krebs",
    "Löwe",
    "Jungfrau",
    "Waage",
    "Skorpion",
    "Schütze",
    "Steinbock",
    "Wassermann",
    "Fische",
]

STEM_TO_ELEMENT = {
    "Jia": "Holz",
    "Yi": "Holz",
    "Bing": "Feuer",
    "Ding": "Feuer",
    "Wu": "Erde",
    "Ji": "Erde",
    "Geng": "Metall",
    "Xin": "Metall",
    "Ren": "Wasser",
    "Gui": "Wasser",
}

BRANCH_TO_ANIMAL = {
    "Zi": "Ratte",
    "Chou": "Ochse",
    "Yin": "Tiger",
    "Mao": "Hase",
    "Chen": "Drache",
    "Si": "Schlange",
    "Wu": "Pferd",
    "Wei": "Ziege",
    "Shen": "Affe",
    "You": "Hahn",
    "Xu": "Hund",
    "Hai": "Schwein",
}


def format_pillar(pillar: Pillar) -> Dict[str, str]:
    stem = STEMS[pillar.stem_index]
    branch = BRANCHES[pillar.branch_index]
    return {
        "stamm": stem,
        "zweig": branch,
        "tier": BRANCH_TO_ANIMAL[branch],
        "element": STEM_TO_ELEMENT[stem],
    }

@app.on_event("startup")
def ensure_ephemeris_data() -> None:
    ensure_ephemeris_files()

class BaziRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time (e.g. 2024-02-10T14:30:00)")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")
    standard: Literal["CIVIL", "LMT"] = "CIVIL"
    boundary: Literal["midnight", "zi"] = "midnight"
    strict: bool = True

class WesternBodyResponse(BaseModel):
    name: str = Field(..., description="Planet name")
    longitude: float = Field(..., description="0-360 degrees")
    latitude: float
    distance: float
    speed: float
    is_retrograde: bool
    zodiac_sign: int
    degree_in_sign: float

class WesternChartResponse(BaseModel):
    jd_ut: float
    house_system: str
    bodies: Dict[str, WesternBodyResponse]
    houses: Dict[str, float]
    angles: Dict[str, float]

class WesternRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "bazi_engine_v2", "version": "0.2.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api")
def api_endpoint(
    datum: str = Query(..., description="Datum im Format YYYY-MM-DD"),
    zeit: str = Query(..., description="Zeit im Format HH:MM[:SS]"),
    ort: Optional[str] = Query(None, description="Ort als 'lat,lon' oder freier Text"),
    tz: str = Query("Europe/Berlin", description="Timezone name"),
    lon: float = Query(13.4050, description="Longitude in degrees"),
    lat: float = Query(52.52, description="Latitude in degrees"),
):
    try:
        if ort:
            if "," in ort:
                parts = [p.strip() for p in ort.split(",", maxsplit=1)]
                if len(parts) == 2:
                    lat = float(parts[0])
                    lon = float(parts[1])
            else:
                raise ValueError("Ort muss als 'lat,lon' angegeben werden, wenn gesetzt.")

        dt = parse_local_iso(f"{datum}T{zeit}", tz, strict=True, fold=0)
        from datetime import timezone

        dt_utc = dt.astimezone(timezone.utc)
        chart = compute_western_chart(dt_utc, lat, lon)
        sun = chart.get("bodies", {}).get("Sun")
        if not sun or "zodiac_sign" not in sun:
            raise ValueError("Sonnenposition konnte nicht berechnet werden.")
        sign_index = int(sun["zodiac_sign"])
        sign_name = ZODIAC_SIGNS_DE[sign_index]
        return {
            "sonne": sign_name,
            "input": {
                "datum": datum,
                "zeit": zeit,
                "ort": ort,
                "tz": tz,
                "lat": lat,
                "lon": lon,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate/bazi")
def calculate_bazi_endpoint(req: BaziRequest):
    try:
        inp = BaziInput(
            birth_local=req.date,
            timezone=req.tz,
            longitude_deg=req.lon,
            latitude_deg=req.lat,
            time_standard=req.standard,
            day_boundary=req.boundary,
            strict_local_time=req.strict,
            fold=0
        )
        res = compute_bazi(inp)

        return {
            "input": req.model_dump(),
            "pillars": {
                "year": format_pillar(res.pillars.year),
                "month": format_pillar(res.pillars.month),
                "day": format_pillar(res.pillars.day),
                "hour": format_pillar(res.pillars.hour),
            },
            "chinese": {
                "year": {
                    "stem": STEMS[res.pillars.year.stem_index],
                    "branch": BRANCHES[res.pillars.year.branch_index],
                    "animal": ANIMALS[res.pillars.year.branch_index],
                },
                "month_master": STEMS[res.pillars.month.stem_index],
                "day_master": STEMS[res.pillars.day.stem_index],
                "hour_master": STEMS[res.pillars.hour.stem_index],
            },
            "dates": {
                "birth_local": res.birth_local_dt.isoformat(),
                "birth_utc": res.birth_utc_dt.isoformat(),
                "lichun_local": res.lichun_local_dt.isoformat()
            },
            "solar_terms_count": len(res.solar_terms_local_dt) if res.solar_terms_local_dt else 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate/western")
def calculate_western_endpoint(req: WesternRequest):
    try:
        # Parse time similar to BaZi
        dt = parse_local_iso(req.date, req.tz, strict=True, fold=0)
        # Convert to utc for ephemeris
        from datetime import timezone
        dt_utc = dt.astimezone(timezone.utc)
        
        chart = compute_western_chart(dt_utc, req.lat, req.lon)
        return chart
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
