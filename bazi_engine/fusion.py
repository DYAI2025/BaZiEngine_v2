# FusionAstrology.py - Wu-Xing + Western Fusion Analysis
# Implements: Planet-to-Element mapping, Wu-Xing vectors, Harmony Index

from __future__ import annotations
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from math import sin, cos, radians, degrees, pi, sqrt, floor

# =============================================================================
# PLANET → WU-XING ELEMENT MAPPING
# =============================================================================
# Classical Western Astrology → Chinese Five Elements (Wu Xing)
# Based on planetary rulerships and elemental associations

PLANET_TO_WUXING = {
    "Sun": "Feuer",        # Fire - Vitality, Life force
    "Moon": "Wasser",      # Water - Emotions, Intuition
    "Mercury": ["Erde", "Metall"],  # Dual - Communication/Mind (Earth for day, Metal for night)
    "Venus": "Metall",     # Metal - Beauty, Value, Form
    "Mars": "Feuer",       # Fire - Action, Energy
    "Jupiter": "Holz",     # Wood - Growth, Expansion, Wisdom
    "Saturn": "Erde",      # Earth - Structure, Limits, Discipline
    "Uranus": "Holz",      # Wood - Innovation, Sudden change (exoteric)
    "Neptune": "Wasser",   # Water - Dreams, Spirituality, Subconscious
    "Pluto": "Feuer",      # Fire - Transformation, Power, Death/Rebirth
    "Chiron": "Wasser",    # Water - Healing, Wounds
    "Lilith": "Wasser",    # Water - Dark Moon, Instincts
    "NorthNode": "Holz",   # Wood - Future direction, Growth path
    "TrueNorthNode": "Holz",
}

# Element order for vector representation (Wu Xing cycle)
WUXING_ORDER = ["Holz", "Feuer", "Erde", "Metall", "Wasser"]
WUXING_INDEX = {elem: i for i, elem in enumerate(WUXING_ORDER)}

# =============================================================================
# WU-XING VECTOR CLASS
# =============================================================================

@dataclass
class WuXingVector:
    """Represents elemental distribution as a normalized 5-dimensional vector."""
    holz: float
    feuer: float
    erde: float
    metall: float
    wasser: float
    
    def to_list(self) -> List[float]:
        return [self.holz, self.feuer, self.erde, self.metall, self.wasser]
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "Holz": self.holz,
            "Feuer": self.feuer,
            "Erde": self.erde,
            "Metall": self.metall,
            "Wasser": self.wasser
        }
    
    def magnitude(self) -> float:
        """Calculate vector magnitude (L2 norm)."""
        return sqrt(sum(x**2 for x in self.to_list()))
    
    def normalize(self) -> WuXingVector:
        """Return normalized unit vector."""
        mag = self.magnitude()
        if mag == 0:
            return self
        return WuXingVector(*[x/mag for x in self.to_list()])
    
    @staticmethod
    def zero() -> WuXingVector:
        return WuXingVector(0, 0, 0, 0, 0)


# =============================================================================
# FUSION ASTROLOGY CALCULATIONS
# =============================================================================

def planet_to_wuxing(planet_name: str, is_night: bool = False) -> str:
    """
    Get Wu-Xing element for a planet.
    
    Args:
        planet_name: Name of the planet
        is_night: Whether it's night time (affects Mercury)
    
    Returns:
        Wu-Xing element name
    """
    element = PLANET_TO_WUXING.get(planet_name, "Erde")  # Default to Earth
    
    if isinstance(element, list):
        # Mercury is dual: Earth by day, Metal by night
        return element[1] if is_night else element[0]
    
    return element


def calculate_wuxing_vector_from_planets(
    bodies: Dict[str, Dict[str, Any]],
    use_retrograde_weight: bool = True
) -> WuXingVector:
    """
    Calculate Wu-Xing vector from planetary positions.

    Args:
        bodies: Dictionary of planetary positions from compute_western_chart()
        use_retrograde_weight: Whether to apply retrograde weighting

    Returns:
        WuXingVector representing elemental distribution
    """
    # Accumulate values in a mutable list [Holz, Feuer, Erde, Metall, Wasser]
    values = [0.0, 0.0, 0.0, 0.0, 0.0]

    # Determine if it's a night chart based on Sun position below horizon
    # For simplicity: check if Sun is in houses 1-6 (below horizon) vs 7-12 (above)
    # A more accurate method would use the Ascendant
    sun_data = bodies.get("Sun", {})
    sun_lon = sun_data.get("longitude", 0)
    # Night chart heuristic: Sun in the lower hemisphere
    # This is a simplification - proper night chart detection requires house positions
    is_night = is_night_chart(sun_lon)

    for planet, data in bodies.items():
        if "error" in data:
            continue

        # Get element for this planet
        is_retrograde = data.get("is_retrograde", False)
        element = planet_to_wuxing(planet, is_night)

        # Base weight: 1.0 for each planet
        weight = 1.0

        # Retrograde planets have stronger/different effect
        if use_retrograde_weight and is_retrograde:
            weight = 1.3  # 30% stronger retrograde influence

        # Add to vector
        idx = WUXING_INDEX[element]
        values[idx] += weight

    return WuXingVector(*values)


def is_night_chart(sun_longitude: float, ascendant: float = None) -> bool:
    """
    Determine if this is a night chart.

    In traditional astrology, a night chart is when the Sun is below the horizon
    (in houses 1-6). Without house positions, we use a simplified heuristic.

    Args:
        sun_longitude: Sun's ecliptic longitude (0-360°)
        ascendant: Ascendant degree (optional, for more accurate calculation)

    Returns:
        True if this appears to be a night chart

    Note:
        This is a simplified heuristic. For accurate night/day determination,
        the actual house position of the Sun should be calculated using the
        Ascendant and local time.
    """
    if ascendant is not None:
        # More accurate: Sun below horizon if it's between ASC and DSC (counter-clockwise)
        # Night = Sun in houses 1-6 (below horizon)
        dsc = (ascendant + 180) % 360
        # Check if Sun is between DSC and ASC (going counter-clockwise = houses 1-6)
        if ascendant > dsc:
            return dsc <= sun_longitude < ascendant
        else:
            return sun_longitude >= dsc or sun_longitude < ascendant
    # Fallback: use a simple seasonal approximation
    # This is NOT accurate for day/night - it's just a placeholder
    # In production, this should be calculated from actual chart data
    return False  # Default to day chart when no ascendant available


def calculate_wuxing_from_bazi(pillars: Dict[str, Dict[str, str]]) -> WuXingVector:
    """
    Extract Wu-Xing vector from Ba Zi pillars.
    
    Each pillar contributes to elements based on:
    - Heavenly Stem: direct element
    - Earthly Branch: hidden elements (up to 3)
    
    Args:
        pillars: Dictionary with year, month, day, hour pillars
    
    Returns:
        WuXingVector from Ba Zi structure
    """
    vector = WuXingVector.zero()
    
    # Element mapping for stems
    STEM_TO_ELEMENT = {
        "Jia": "Holz", "Yi": "Holz",  # Wood
        "Bing": "Feuer", "Ding": "Feuer",  # Fire
        "Wu": "Erde", "Ji": "Erde",  # Earth
        "Geng": "Metall", "Xin": "Metall",  # Metal
        "Ren": "Wasser", "Gui": "Wasser"  # Water
    }
    
    # Hidden stems in branches (藏干) with traditional weights
    # Main Qi (主气): 1.0, Middle Qi (中气): 0.5, Residual Qi (余气): 0.3
    BRANCH_HIDDEN = {
        "Zi": [("Wasser", 1.0)],                                       # 子: Gui (癸) Water
        "Chou": [("Erde", 1.0), ("Wasser", 0.5), ("Metall", 0.3)],    # 丑: Ji (己) Earth, Gui (癸) Water, Xin (辛) Metal
        "Yin": [("Holz", 1.0), ("Feuer", 0.5), ("Erde", 0.3)],        # 寅: Jia (甲) Wood, Bing (丙) Fire, Wu (戊) Earth
        "Mao": [("Holz", 1.0)],                                        # 卯: Yi (乙) Wood
        "Chen": [("Erde", 1.0), ("Holz", 0.5), ("Wasser", 0.3)],      # 辰: Wu (戊) Earth, Yi (乙) Wood, Gui (癸) Water
        "Si": [("Feuer", 1.0), ("Metall", 0.5), ("Erde", 0.3)],       # 巳: Bing (丙) Fire, Geng (庚) Metal, Wu (戊) Earth
        "Wu": [("Feuer", 1.0), ("Erde", 0.5)],                        # 午: Ding (丁) Fire, Ji (己) Earth
        "Wei": [("Erde", 1.0), ("Feuer", 0.5), ("Holz", 0.3)],        # 未: Ji (己) Earth, Ding (丁) Fire, Yi (乙) Wood
        "Shen": [("Metall", 1.0), ("Wasser", 0.5), ("Erde", 0.3)],    # 申: Geng (庚) Metal, Ren (壬) Water, Wu (戊) Earth
        "You": [("Metall", 1.0)],                                      # 酉: Xin (辛) Metal
        "Xu": [("Erde", 1.0), ("Metall", 0.5), ("Feuer", 0.3)],       # 戌: Wu (戊) Earth, Xin (辛) Metal, Ding (丁) Fire
        "Hai": [("Wasser", 1.0), ("Holz", 0.5)]                       # 亥: Ren (壬) Water, Jia (甲) Wood
    }
    
    for pillar_name, pillar_data in pillars.items():
        stem = pillar_data.get("stem", pillar_data.get("stamm", ""))
        branch = pillar_data.get("branch", pillar_data.get("zweig", ""))
        
        # Add stem element (weight: 1.0)
        if stem in STEM_TO_ELEMENT:
            elem = STEM_TO_ELEMENT[stem]
            idx = WUXING_INDEX[elem]
            values = vector.to_list()
            values[idx] += 1.0
            vector = WuXingVector(*values)
        
        # Add hidden branch elements
        if branch in BRANCH_HIDDEN:
            for elem, weight in BRANCH_HIDDEN[branch]:
                idx = WUXING_INDEX[elem]
                values = vector.to_list()
                values[idx] += weight
                vector = WuXingVector(*values)
    
    return vector


def calculate_harmony_index(
    western_vector: WuXingVector,
    bazi_vector: WuXingVector,
    method: str = "dot_product"
) -> Dict[str, Any]:
    """
    Calculate Harmony Index between Western and Ba Zi charts.
    
    Args:
        western_vector: Wu-Xing vector from western planets
        bazi_vector: Wu-Xing vector from Ba Zi pillars
        method: "dot_product" or "cosine"
    
    Returns:
        Dictionary with harmony metrics
    """
    # Normalize vectors
    w_norm = western_vector.normalize()
    b_norm = bazi_vector.normalize()
    
    if method == "dot_product":
        # Dot product of normalized vectors
        # Range: -1 to 1, but with our positive-only vectors: 0 to 1
        dot = sum(w * b for w, b in zip(w_norm.to_list(), b_norm.to_list()))
        
        # Cosine similarity is equivalent for normalized vectors
        harmony = max(0, dot)  # Clamp to 0-1 range
        
    elif method == "cosine":
        # Cosine similarity
        mag_w = western_vector.magnitude()
        mag_b = bazi_vector.magnitude()
        if mag_w == 0 or mag_b == 0:
            harmony = 0.0
        else:
            dot = sum(w * b for w, b in zip(western_vector.to_list(), bazi_vector.to_list()))
            harmony = dot / (mag_w * mag_b)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return {
        "harmony_index": round(harmony, 4),
        "interpretation": interpret_harmony(harmony),
        "method": method,
        "western_vector": w_norm.to_dict(),
        "bazi_vector": b_norm.to_dict()
    }


def interpret_harmony(h: float) -> str:
    """Interpret harmony index value."""
    if h >= 0.8:
        return "Starke Resonanz - Westliche und östliche Matrix stehen in perfekter Harmonie"
    elif h >= 0.6:
        return "Gute Harmonie - Die Energien unterstützen sich gegenseitig"
    elif h >= 0.4:
        return "Moderate Balance - Unterschiedliche Schwerpunkte, aber keine Konflikte"
    elif h >= 0.2:
        return "Gespannte Harmonie - Teils komplementär, teils divergierend"
    else:
        return "Divergenz - Westliche und östliche Energien arbeiten in unterschiedliche Richtungen"


# =============================================================================
# EQUATION OF TIME (Zeitgleichung)
# =============================================================================

def equation_of_time(day_of_year: int, use_precise: bool = True) -> float:
    """
    Calculate Equation of Time (E_t) in minutes.

    The Equation of Time quantifies the discrepancy between
    apparent solar time and mean solar time due to:
    1. Earth's elliptical orbit (eccentricity effect)
    2. Earth's axial tilt (obliquity effect)

    Args:
        day_of_year: Day number (1-366)
        use_precise: If True, use more accurate formula with both effects

    Returns:
        Equation of Time in minutes (can be positive or negative)
        Range: approximately -14.2 to +16.4 minutes

    Formula (standard approximation):
        E_t = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)
        where B = 360*(N-81)/365 degrees

    More precise formula separates eccentricity and obliquity effects.
    """
    if use_precise:
        # More accurate formula using both eccentricity and obliquity
        # Reference: NOAA Solar Calculator / Astronomical Algorithms
        # Fractional year in radians
        gamma = 2 * pi * (day_of_year - 1) / 365.0

        # Equation of time in minutes (more accurate Fourier series)
        E = 229.18 * (
            0.000075
            + 0.001868 * cos(gamma)
            - 0.032077 * sin(gamma)
            - 0.014615 * cos(2 * gamma)
            - 0.040849 * sin(2 * gamma)
        )
        return round(E, 3)
    else:
        # Simplified formula
        B = 360 * (day_of_year - 81) / 365
        B_rad = radians(B)

        E = (9.87 * sin(2 * B_rad)
             - 7.53 * cos(B_rad)
             - 1.5 * sin(B_rad))

        return round(E, 2)


def true_solar_time(
    civil_time_hours: float,
    longitude_deg: float,
    day_of_year: int,
    timezone_offset_hours: float = None
) -> float:
    """
    Calculate True Solar Time (TST) from civil time.

    TST = Local Mean Time + Equation of Time
    LMT = UTC + (longitude / 15) hours

    For civil time with a timezone:
    TST = civil_time - tz_offset + (longitude/15) + E_t

    Args:
        civil_time_hours: Local civil time in hours (e.g., 14.5 = 14:30)
        longitude_deg: Longitude (positive = east, negative = west)
        day_of_year: Day of year (1-366)
        timezone_offset_hours: Timezone offset from UTC in hours (e.g., +1 for CET).
                              If None, uses longitude-based calculation for LMT input.

    Returns:
        True Solar Time in hours (0-24)

    Note:
        For accurate BaZi hour pillar calculations, TST should be used instead
        of civil time, as the Chinese hour system is based on solar position.

    Example:
        For Berlin (lon=13.4°, tz=+1):
        - Civil time: 14:30 (14.5 hours)
        - TST ≈ 14:30 - 1h (tz) + 0.893h (lon/15) + E_t
    """
    if timezone_offset_hours is not None:
        # Convert civil time to UTC, then to LMT
        # UTC = civil_time - timezone_offset
        # LMT = UTC + longitude/15
        utc_hours = civil_time_hours - timezone_offset_hours
        lmt_hours = utc_hours + (longitude_deg / 15.0)
    else:
        # Assume input is already LMT or use simple longitude correction
        # Longitude correction: 4 minutes per degree = 1 hour per 15 degrees
        lmt_hours = civil_time_hours + (longitude_deg / 15.0) - (longitude_deg / 15.0)
        # Simplified: for LMT input, TST = LMT + E_t
        lmt_hours = civil_time_hours

    # Equation of Time in hours
    E_t = equation_of_time(day_of_year) / 60.0

    # True Solar Time = Local Mean Time + Equation of Time
    TST = lmt_hours + E_t

    # Normalize to 0-24 range
    while TST < 0:
        TST += 24
    while TST >= 24:
        TST -= 24

    return round(TST, 4)


def true_solar_time_from_civil(
    civil_time_hours: float,
    longitude_deg: float,
    day_of_year: int,
    standard_meridian_deg: float = None
) -> float:
    """
    Calculate True Solar Time from civil time with timezone standard meridian.

    This is the correct formula for converting civil (clock) time to solar time:
    TST = civil_time + 4*(standard_meridian - longitude) + E_t

    The 4 minutes/degree factor converts the longitude difference to time.

    Args:
        civil_time_hours: Local civil time in hours
        longitude_deg: Observer's longitude (positive = east)
        day_of_year: Day of year (1-366)
        standard_meridian_deg: Standard meridian for the timezone (e.g., 15° for CET).
                              If None, calculated from typical timezone offsets.

    Returns:
        True Solar Time in hours

    Example:
        Berlin (lon=13.405°, standard_meridian=15° for CET):
        TST = civil_time + 4*(15-13.405)/60 + E_t
            = civil_time + 0.106h + E_t
    """
    if standard_meridian_deg is None:
        # Estimate standard meridian from longitude
        # Standard time zones are typically at 15° intervals
        standard_meridian_deg = round(longitude_deg / 15) * 15

    # Longitude correction: difference from standard meridian
    # 4 minutes per degree = 1/15 hours per degree
    longitude_correction_hours = (standard_meridian_deg - longitude_deg) * 4 / 60

    # Equation of Time
    E_t_hours = equation_of_time(day_of_year) / 60.0

    # True Solar Time
    TST = civil_time_hours + longitude_correction_hours + E_t_hours

    # Normalize to 0-24 range
    while TST < 0:
        TST += 24
    while TST >= 24:
        TST -= 24

    return round(TST, 4)


# =============================================================================
# MAIN FUSION ANALYSIS FUNCTION
# =============================================================================

def compute_fusion_analysis(
    birth_utc_dt: Any,
    latitude: float,
    longitude: float,
    bazi_pillars: Dict[str, Dict[str, str]],
    western_bodies: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Complete Fusion Astrology Analysis.
    
    Combines Western planetary data with Ba Zi pillars to create
    a unified energetic profile.
    
    Args:
        birth_utc_dt: Birth datetime in UTC
        latitude: Birth latitude
        longitude: Birth longitude  
        bazi_pillars: Ba Zi pillars (year, month, day, hour)
        western_bodies: Planetary positions from compute_western_chart()
    
    Returns:
        Complete fusion analysis with Wu-Xing vectors and harmony index
    """
    # 1. Calculate Wu-Xing vectors
    western_wuxing = calculate_wuxing_vector_from_planets(western_bodies)
    bazi_wuxing = calculate_wuxing_from_bazi(bazi_pillars)
    
    # 2. Calculate harmony index
    harmony = calculate_harmony_index(western_wuxing, bazi_wuxing)
    
    # 3. Calculate additional fusion metrics
    western_normalized = western_wuxing.normalize()
    bazi_normalized = bazi_wuxing.normalize()
    
    # Elemental strengths comparison
    elemental_comparison = {}
    for elem in WUXING_ORDER:
        w_val = getattr(western_normalized, elem.lower())
        b_val = getattr(bazi_normalized, elem.lower())
        elemental_comparison[elem] = {
            "western": round(w_val, 3),
            "bazi": round(b_val, 3),
            "difference": round(w_val - b_val, 3)
        }
    
    # 4. Cosmic State (simplified)
    # Sum of elemental energies weighted by their balance
    cosmic_state = sum(
        w * b for w, b in zip(western_normalized.to_list(), bazi_normalized.to_list())
    )
    
    return {
        "wu_xing_vectors": {
            "western_planets": western_normalized.to_dict(),
            "bazi_pillars": bazi_normalized.to_dict()
        },
        "harmony_index": harmony,
        "elemental_comparison": elemental_comparison,
        "cosmic_state": round(cosmic_state, 4),
        "fusion_interpretation": generate_fusion_interpretation(
            harmony["harmony_index"],
            elemental_comparison,
            western_wuxing,
            bazi_wuxing
        )
    }


def generate_fusion_interpretation(
    harmony: float,
    comparison: Dict[str, Dict[str, float]],
    western: WuXingVector,
    bazi: WuXingVector
) -> str:
    """Generate textual interpretation of fusion analysis.

    Args:
        harmony: Harmony index as float (0.0 to 1.0)
        comparison: Element comparison dictionary
        western: Western Wu-Xing vector
        bazi: BaZi Wu-Xing vector

    Returns:
        Formatted interpretation string
    """
    # Find dominant elements
    w_dict = western.to_dict()
    b_dict = bazi.to_dict()
    w_dominant = max(w_dict, key=w_dict.get)
    b_dominant = max(b_dict, key=b_dict.get)

    lines = [
        f"Harmonie-Index: {harmony:.2%}",
        interpret_harmony(harmony),
        "",
        f"Westliche Dominanz: {w_dominant}",
        f"Östliche Dominanz: {b_dominant}",
        ""
    ]

    # Add specific guidance
    if harmony >= 0.6:
        lines.append("Ihre westliche und östliche Chart stehen in starker Resonanz.")
        lines.append("Die Energien ergänzen sich harmonisch.")
    elif harmony >= 0.3:
        lines.append("Ihre Charts zeigen eine interessante Balance zwischen Ost und West.")
        lines.append("Es gibt Spannungen, aber auch Wachstumspotential.")
    else:
        lines.append("Ihre westliche und östliche Energie arbeiten in unterschiedliche Richtungen.")
        lines.append("Integration erfordert bewusste Arbeit.")

    return "\n".join(lines)
