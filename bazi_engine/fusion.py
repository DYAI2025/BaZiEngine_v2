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
    vector = WuXingVector.zero()
    
    for planet, data in bodies.items():
        if "error" in data:
            continue
            
        # Get element for this planet
        is_retrograde = data.get("is_retrograde", False)
        is_night = is_night_time(data.get("longitude", 0))
        element = planet_to_wuxing(planet, is_night)
        
        # Base weight: 1.0 for each planet
        weight = 1.0
        
        # Retrograde planets have stronger/different effect
        if use_retrograde_weight and is_retrograde:
            weight = 1.3  # 30% stronger retrograde influence
        
        # Add to vector
        idx = WUXING_INDEX[element]
        current_values = vector.to_list()
        current_values[idx] += weight
    
    return WuXingVector(*vector.to_list())


def is_night_time(sun_longitude: float) -> bool:
    """
    Determine if given longitude is in "night" time (after sunset).
    Simplified: Night is roughly 6 PM to 6 AM (180° to 0°/360°).
    
    More precise: Based on actual sunset at location, but this is a simplified version.
    """
    # Simplified: Night is when Sun is below horizon (approximate)
    # 0° = Spring Equinox, Sun at zenith at noon
    # Night = Sun between 180° and 360° (roughly 6 PM to 6 AM)
    return 180 <= sun_longitude < 360


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
    
    # Hidden elements in branches (strength: 1, 0.5, 0.25)
    BRANCH_HIDDEN = {
        "Zi": [("Wasser", 1.0)],                    # Rat
        "Chou": [("Erde", 0.5), ("Wasser", 0.5)],  # Ox
        "Yin": [("Holz", 1.0), ("Feuer", 0.5)],    # Tiger
        "Mao": [("Holz", 1.0)],                    # Rabbit
        "Chen": [("Erde", 0.5), ("Metall", 0.5)],  # Dragon
        "Si": [("Feuer", 1.0)],                     # Snake
        "Wu": [("Feuer", 1.0), ("Erde", 0.5)],     # Horse
        "Wei": [("Erde", 0.5), ("Metall", 0.5)],   # Goat
        "Shen": [("Metall", 1.0), ("Wasser", 0.5)], # Monkey
        "You": [("Metall", 1.0)],                  # Rooster
        "Xu": [("Erde", 0.5), ("Metall", 0.5)],    # Dog
        "Hai": [("Wasser", 1.0)]                   # Pig
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

def equation_of_time(day_of_year: int) -> float:
    """
    Calculate Equation of Time (E_t) in minutes.
    
    The Equation of Time quantifies the discrepancy between
    apparent solar time and mean solar time.
    
    Args:
        day_of_year: Day number (1-365)
    
    Returns:
        Equation of Time in minutes (can be positive or negative)
    
    Formula (approximate):
    E_t = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)
    where B = 360*(N-81)/365 degrees
    """
    B = 360 * (day_of_year - 81) / 365
    B_rad = radians(B)
    
    E = (9.87 * sin(2 * B_rad) 
         - 7.53 * cos(B_rad) 
         - 1.5 * sin(B_rad))
    
    return round(E, 2)


def true_solar_time(
    civil_time_hours: float,
    longitude_deg: float,
    day_of_year: int
) -> float:
    """
    Calculate True Solar Time (TST) from civil time.
    
    TST = T_civil + ΔT_long + E_t
    
    Where:
    - T_civil: Civil/civilian time
    - ΔT_long: Longitude correction (4 minutes per degree, + for east, - for west)
    - E_t: Equation of Time (in minutes)
    
    Args:
        civil_time_hours: Time in hours (e.g., 14.5 = 14:30)
        longitude_deg: Longitude (positive = east, negative = west)
        day_of_year: Day of year (1-365)
    
    Returns:
        True Solar Time in hours
    """
    # Longitude correction: 4 minutes per degree
    # East = ahead of UTC, so add time
    # West = behind UTC, so subtract time
    delta_t_long = longitude_deg * 4 / 60  # Convert to hours
    
    # Equation of Time in hours
    E_t = equation_of_time(day_of_year) / 60
    
    # True Solar Time
    TST = civil_time_hours + delta_t_long + E_t
    
    # Normalize to 0-24 range
    TST = TST % 24
    
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
    western_wuxing = calculate_wuxing_from_planets(western_bodies)
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
    """Generate textual interpretation of fusion analysis."""
    
    # Find dominant elements
    w_dominant = max(western.to_dict(), key=western.to_dict().get)
    b_dominant = max(bazi.to_dict(), key=bazi.to_dict().get)
    
    lines = [
        f"Harmonie-Index: {harmony:.2%}",
        harmony["interpretation"] if isinstance(harmony, dict) else interpret_harmony(harmony),
        "",
        f"Westliche Dominanz: {w_dominant}",
        f"Östliche Dominanz: {b_dominant}",
        ""
    ]
    
    # Add specific guidance
    if harmony >= 0.6:
        lines.append("🌟 Ihre westliche und östliche chart stehen in starker Resonanz.")
        lines.append("Die Energien ergänzen sich harmonisch.")
    elif harmony >= 0.3:
        lines.append("⚖️ Ihre Chart zeigen eine interessante Balance zwischen Ost und West.")
        lines.append("Es gibt Spannungen, aber auch Wachstumspotential.")
    else:
        lines.append("🌊 Ihre westliche und östliche Energie arbeiten in unterschiedliche Richtungen.")
        lines.append("Integration erfordert bewusste Arbeit.")
    
    return "\n".join(lines)
