from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from datetime import datetime

from .types import BaziInput
from .bazi import compute_bazi
from .western import compute_western_chart
from .time_utils import parse_local_iso
from .ephemeris import ensure_ephemeris_files

app = FastAPI(
    title="BaZi Engine v2 API",
    description="API for BaZi (Chinese Astrology) and Basic Western Astrology calculations.",
    version="0.2.0"
)

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
                "year": str(res.pillars.year),
                "month": str(res.pillars.month),
                "day": str(res.pillars.day),
                "hour": str(res.pillars.hour)
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
