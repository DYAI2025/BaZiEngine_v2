from contextlib import asynccontextmanager
import os
import hmac
import hashlib
import time
from fastapi import FastAPI, HTTPException, Query, Request, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timezone
from .types import BaziInput, Pillar
from .constants import STEMS, BRANCHES, ANIMALS
from .bazi import compute_bazi
from .western import compute_western_chart
from .fusion import (
    compute_fusion_analysis,
    PLANET_TO_WUXING,
    WUXING_ORDER,
    WuXingVector,
    equation_of_time,
    true_solar_time,
    calculate_wuxing_vector_from_planets,
    calculate_wuxing_from_bazi,
    calculate_harmony_index
)
from .time_utils import parse_local_iso
from .ephemeris import ensure_ephemeris_files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - ensures ephemeris files are available on startup."""
    ensure_ephemeris_files()
    yield


app = FastAPI(
    title="BaZi Engine v2 API",
    description="API for BaZi (Chinese Astrology) and Basic Western Astrology calculations.",
    version="0.2.0",
    lifespan=lifespan
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
        dt_utc = dt.astimezone(timezone.utc)
        
        chart = compute_western_chart(dt_utc, req.lat, req.lon)
        return chart
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# FUSION ASTROLOGY ENDPOINTS
# =============================================================================

class FusionRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")
    bazi_pillars: Dict[str, Dict[str, str]] = Field(
        ..., 
        description="Ba Zi pillars from /calculate/bazi endpoint"
    )

class FusionResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vectors: Dict[str, Dict[str, float]]
    harmony_index: Dict[str, Any]
    elemental_comparison: Dict[str, Dict[str, float]]
    cosmic_state: float
    fusion_interpretation: str

@app.post("/calculate/fusion", response_model=FusionResponse)
def calculate_fusion_endpoint(req: FusionRequest):
    """
    Fusion Astrology Analysis - Wu-Xing + Western Integration.
    
    Calculates the harmony between western planetary energies and
    chinese Ba Zi elemental structure using vector mathematics.
    
    Returns:
    - Wu-Xing vectors for both systems
    - Harmony Index (0-1 scale)
    - Element-by-element comparison
    - Cosmic State metric
    - Interpretation
    """
    try:
        # Parse time
        dt = parse_local_iso(req.date, req.tz, strict=True, fold=0)
        dt_utc = dt.astimezone(timezone.utc)
        
        # Get western chart
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)
        
        # Compute fusion analysis
        fusion = compute_fusion_analysis(
            birth_utc_dt=dt_utc,
            latitude=req.lat,
            longitude=req.lon,
            bazi_pillars=req.bazi_pillars,
            western_bodies=western_chart["bodies"]
        )
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon,
                "lat": req.lat
            },
            "wu_xing_vectors": fusion["wu_xing_vectors"],
            "harmony_index": fusion["harmony_index"],
            "elemental_comparison": fusion["elemental_comparison"],
            "cosmic_state": fusion["cosmic_state"],
            "fusion_interpretation": fusion["fusion_interpretation"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class WxRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")

class WxResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vector: Dict[str, float]
    dominant_element: str
    equation_of_time: float
    true_solar_time: float

@app.post("/calculate/wuxing", response_model=WxResponse)
def calculate_wuxing_endpoint(req: WxRequest):
    """
    Calculate Wu-Xing Element Vector from Western Planets.
    
    Maps planetary positions to Five Elements (Wu Xing) and
    returns the elemental distribution vector.
    """
    try:
        # Parse time
        dt = parse_local_iso(req.date, req.tz, strict=True, fold=0)
        dt_utc = dt.astimezone(timezone.utc)
        
        # Get western chart
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)
        
        # Calculate Wu-Xing vector
        wx_vector = calculate_wuxing_vector_from_planets(western_chart["bodies"])
        wx_normalized = wx_vector.normalize()
        
        # Get day of year for equation of time
        day_of_year = dt.timetuple().tm_yday
        
        # Calculate TST
        civil_time_hours = dt.hour + dt.minute / 60
        TST = true_solar_time(civil_time_hours, req.lon, day_of_year)
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon,
                "lat": req.lat
            },
            "wu_xing_vector": wx_normalized.to_dict(),
            "dominant_element": max(wx_normalized.to_dict(), key=wx_normalized.to_dict().get),
            "equation_of_time": equation_of_time(day_of_year),
            "true_solar_time": TST
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class TSTRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")

class TSTResponse(BaseModel):
    input: Dict[str, Any]
    civil_time_hours: float
    longitude_correction_hours: float
    equation_of_time_hours: float
    true_solar_time_hours: float
    true_solar_time_formatted: str

@app.post("/calculate/tst", response_model=TSTResponse)
def calculate_tst_endpoint(req: TSTRequest):
    """
    Calculate True Solar Time (TST).
    
    Applies Equation of Time and longitude correction to convert
    civil time to astronomically correct solar time.
    
    Essential for accurate Ba Zi hour pillar calculations.
    """
    try:
        # Parse time
        dt = parse_local_iso(req.date, req.tz, strict=True, fold=0)
        
        # Get day of year
        day_of_year = dt.timetuple().tm_yday
        
        # Civil time in hours
        civil_hours = dt.hour + dt.minute / 60 + dt.second / 3600
        
        # Longitude correction
        delta_t_long = req.lon * 4 / 60  # 4 minutes per degree
        
        # Equation of Time
        E_t = equation_of_time(day_of_year) / 60  # Convert to hours
        
        # True Solar Time
        TST = civil_hours + delta_t_long + E_t
        TST = TST % 24
        
        # Format TST as HH:MM
        hours = int(TST)
        minutes = int((TST - hours) * 60)
        tst_formatted = f"{hours:02d}:{minutes:02d}"
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon
            },
            "civil_time_hours": round(civil_hours, 4),
            "longitude_correction_hours": round(delta_t_long, 4),
            "equation_of_time_hours": round(E_t, 4),
            "true_solar_time_hours": round(TST, 4),
            "true_solar_time_formatted": tst_formatted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/info/wuxing-mapping")
def get_wuxing_mapping():
    """
    Get the planet to Wu-Xing element mapping used by this API.
    """
    return {
        "mapping": PLANET_TO_WUXING,
        "order": WUXING_ORDER,
        "description": {
            "PLANET_TO_WUXING": "Western planet to Chinese element mapping",
            "WUXING_ORDER": "Wu Xing cycle order: Holz -> Feuer -> Erde -> Metall -> Wasser"
        }
    }


# =============================================================================
# ELEVENLABS WEBHOOK ENDPOINT
# =============================================================================

class ElevenLabsChartRequest(BaseModel):
    birthDate: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birthTime: Optional[str] = Field(None, description="Birth time in HH:MM format (optional)")


def verify_elevenlabs_signature(
    payload: bytes,
    signature_header: Optional[str],
    secret: str,
    tolerance_ms: int = 300000  # 5 minutes
) -> bool:
    """Verify HMAC signature from ElevenLabs-Signature header."""
    if not signature_header:
        return False

    # Parse signature header: "t=<timestamp>,v1=<signature>"
    parts = signature_header.split(',')
    timestamp_part = next((p for p in parts if p.startswith('t=')), None)
    signature_part = next((p for p in parts if p.startswith('v1=')), None)

    if not timestamp_part or not signature_part:
        return False

    timestamp = int(timestamp_part.split('=')[1])
    provided_signature = signature_part.split('=')[1]

    # Check timestamp tolerance
    now = int(time.time() * 1000)
    if abs(now - timestamp) > tolerance_ms:
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode() + payload
    expected_signature = hmac.new(
        secret.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(provided_signature, expected_signature)


@app.post("/api/webhooks/chart")
async def elevenlabs_chart_webhook(
    request: Request,
    elevenlabs_signature: Optional[str] = Header(None, alias="elevenlabs-signature"),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    authorization: Optional[str] = Header(None)
):
    """
    ElevenLabs Agent Tool: Get Astrology Chart

    Returns Western zodiac sign and Chinese BaZi data for a birth date.
    Supports multiple auth methods: HMAC signature, API key header, or Bearer token.
    """
    tool_secret = os.environ.get("ELEVENLABS_TOOL_SECRET")

    if not tool_secret:
        raise HTTPException(status_code=500, detail="ELEVENLABS_TOOL_SECRET not configured")

    # Get raw body for signature verification
    raw_body = await request.body()

    # Try multiple authentication methods
    auth_valid = False

    # Method 1: HMAC signature (preferred)
    if elevenlabs_signature:
        auth_valid = verify_elevenlabs_signature(raw_body, elevenlabs_signature, tool_secret)

    # Method 2: Simple API key header
    if not auth_valid and x_api_key:
        auth_valid = hmac.compare_digest(x_api_key, tool_secret)

    # Method 3: Bearer token
    if not auth_valid and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            auth_valid = hmac.compare_digest(token, tool_secret)

    if not auth_valid:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    # Parse request
    try:
        import json
        data = json.loads(raw_body)
        req = ElevenLabsChartRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    # Build datetime string
    birth_time = req.birthTime or "12:00"
    datetime_str = f"{req.birthDate}T{birth_time}:00"

    try:
        # Parse and calculate
        dt = parse_local_iso(datetime_str, "Europe/Berlin", strict=False, fold=0)
        dt_utc = dt.astimezone(timezone.utc)

        # Calculate Western chart
        western_chart = compute_western_chart(dt_utc, 52.52, 13.405)  # Default: Berlin
        sun = western_chart.get("bodies", {}).get("Sun", {})
        moon = western_chart.get("bodies", {}).get("Moon", {})

        sun_sign_idx = int(sun.get("zodiac_sign", 0))
        moon_sign_idx = int(moon.get("zodiac_sign", 0))
        sun_sign = ZODIAC_SIGNS_DE[sun_sign_idx]
        moon_sign = ZODIAC_SIGNS_DE[moon_sign_idx]

        # Calculate BaZi
        inp = BaziInput(
            birth_local=datetime_str,
            timezone="Europe/Berlin",
            longitude_deg=13.405,
            latitude_deg=52.52,
            time_standard="CIVIL",
            day_boundary="midnight",
            strict_local_time=False,
            fold=0
        )
        bazi_result = compute_bazi(inp)

        # Format BaZi pillars
        year_pillar = format_pillar(bazi_result.pillars.year)
        month_pillar = format_pillar(bazi_result.pillars.month)
        day_pillar = format_pillar(bazi_result.pillars.day)
        hour_pillar = format_pillar(bazi_result.pillars.hour)

        return {
            "western": {
                "sunSign": sun_sign,
                "moonSign": moon_sign,
                "sunSignEnglish": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                   "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sun_sign_idx],
            },
            "eastern": {
                "yearAnimal": year_pillar["tier"],
                "yearElement": year_pillar["element"],
                "monthAnimal": month_pillar["tier"],
                "dayAnimal": day_pillar["tier"],
                "dayElement": day_pillar["element"],
                "dayMaster": day_pillar["stamm"],
            },
            "summary": {
                "sternzeichen": sun_sign,
                "chinesischesZeichen": f"{year_pillar['element']} {year_pillar['tier']}",
                "tagesmeister": f"{day_pillar['element']} ({day_pillar['stamm']})",
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
