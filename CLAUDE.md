# CLAUDE.md - AI Assistant Guide for BaZi Engine v0.2

This documentation provides comprehensive guidance for AI assistants (like Claude) working on the BaZi Engine codebase. It covers project structure, development workflows, key conventions, common tasks, and important gotchas.

---

## PROJECT OVERVIEW

**BaZi Engine** is a deterministic astronomical calculation engine for Chinese astrology (Four Pillars of Destiny). It calculates Year, Month, Day, and Hour pillars based on precise astronomical solar-term boundaries using the Swiss Ephemeris library.

**Key Characteristics:**
- **Deterministic**: No randomness, purely astronomical calculations
- **Test-first**: Golden vector validation with known correct results
- **Immutable**: Frozen dataclasses throughout
- **Type-safe**: Complete type hint coverage (Python 3.10+)
- **Functional**: Pure functions with no side effects
- **Version**: 0.2.0

**Main Technologies:**
- Python 3.10+ (required)
- Swiss Ephemeris (pyswisseph) for astronomical calculations
- FastAPI + Uvicorn for REST API
- pytest for testing
- Docker for containerization
- Fly.io for deployment

---

## PROJECT STRUCTURE

```
BaZiEngine_v2/
├── bazi_engine/          # Main package (746 LOC)
│   ├── __init__.py       # Package exports
│   ├── types.py          # Data structures (75 LOC)
│   ├── constants.py      # Stems/Branches (6 LOC)
│   ├── bazi.py           # Core calculation engine (149 LOC)
│   ├── ephemeris.py      # Swiss Ephemeris backend (70 LOC)
│   ├── jieqi.py          # Solar term calculations (98 LOC)
│   ├── time_utils.py     # Time parsing/conversion (41 LOC)
│   ├── app.py            # FastAPI REST API (106 LOC)
│   ├── cli.py            # Command-line interface (66 LOC)
│   └── western.py        # Western astrology (120 LOC)
├── tests/                # Test suite
│   ├── test_golden.py           # Golden vector tests
│   ├── test_golden_vectors.py   # Extended test cases
│   └── test_invariants.py       # Invariant validation
├── .github/workflows/    # CI/CD
│   └── ci.yml            # GitHub Actions
├── benchmark_performance.py  # Performance benchmarking
├── Dockerfile            # Container image
├── fly.toml              # Fly.io deployment config
├── pyproject.toml        # Build configuration
├── .gitignore            # Version control exclusions
├── README.md             # Quick start guide
├── QWEN.md               # AI assistant context (Qwen-specific)
├── ARCHITECTURE_DE.md    # German architecture docs (36KB)
├── PERFORMANCE_ANALYSIS_DE.md  # German performance analysis (11KB)
└── CLAUDE.md             # This file - Claude assistant guide
```

### Module Dependencies

```
constants.py ← types.py ← (all other modules)
ephemeris.py ← jieqi.py ← bazi.py
time_utils.py ← bazi.py
app.py (imports bazi.py, western.py)
cli.py (imports bazi.py)
```

**Rule**: Never import `bazi.py` into lower-level modules to avoid circular dependencies.

---

## CORE CONCEPTS

### Entry Point

The main entry point is `compute_bazi()` in `bazi_engine/bazi.py:46`:

```python
from bazi_engine import compute_bazi, BaziInput

result = compute_bazi(BaziInput(
    birth_local="2024-02-10T14:30:00",
    timezone="Europe/Berlin",
    longitude_deg=13.4050,
    latitude_deg=52.52,
))
```

### Calculation Pipeline (9 Steps)

The `compute_bazi()` function implements this pipeline:

1. **Parse local time** - Convert ISO 8601 to datetime with timezone validation
2. **Convert to UTC** - Handle DST with optional strict mode
3. **Convert to chart-local** - Apply CIVIL or LMT time standard
4. **Calculate Julian Days** - UT and TT for astronomical calculations
5. **Year Pillar** - Based on LiChun (Start of Spring at 315° solar longitude)
6. **Month Pillar** - Based on 12 Jie crossings (315°, 345°, 15°, ...)
7. **Day Pillar** - JDN-based sexagenary 60-day cycle
8. **Hour Pillar** - 2-hour branches derived from day stem
9. **Optional: 24 Solar Terms** - Diagnostic cross-validation

### Data Structures

All data structures use **frozen dataclasses** for immutability:

```python
@dataclass(frozen=True)
class Pillar:
    stem_index: int    # 0-9 (Jia=0, Yi=1, Bing=2, ...)
    branch_index: int  # 0-11 (Zi=0, Chou=1, Yin=2, ...)

@dataclass(frozen=True)
class FourPillars:
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar

@dataclass(frozen=True)
class BaziInput:
    birth_local: str              # ISO 8601 local datetime
    timezone: str                 # IANA timezone (e.g., "Europe/Berlin")
    longitude_deg: float          # -180 to +180
    latitude_deg: float           # -90 to +90
    time_standard: TimeStandard   # "CIVIL" or "LMT"
    day_boundary: DayBoundary     # "midnight" or "zi"
    strict_local_time: bool       # DST validation (default: True)
    fold: Fold                    # 0 or 1 for ambiguous times
    ephe_path: Optional[str]      # Custom ephemeris path

@dataclass(frozen=True)
class BaziResult:
    input: BaziInput
    pillars: FourPillars
    birth_local_dt: datetime
    birth_utc_dt: datetime
    chart_local_dt: datetime
    jd_ut: float                  # Julian Day (Universal Time)
    jd_tt: float                  # Julian Day (Terrestrial Time)
    delta_t_seconds: float        # ΔT correction
    lichun_local_dt: datetime     # LiChun (year boundary)
    month_boundaries_local_dt: Sequence[datetime]  # 13 boundaries
    month_index: int              # 0-11
    solar_terms_local_dt: Optional[Sequence[SolarTerm]]  # Diagnostic
```

**Constants** (bazi_engine/constants.py):
```python
STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
BRANCHES = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
DAY_OFFSET = 49  # Calibration constant for JDN → sexagenary alignment
```

---

## DEVELOPMENT WORKFLOWS

### Local Development Setup

```bash
# Clone repository (if not already cloned)
git clone <repo-url>
cd BaZiEngine_v2

# Check current branch
git branch

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "from bazi_engine import compute_bazi; print('OK')"

# Run tests
pytest -q

# Run with verbose output
pytest -v
```

### Running the Application

**CLI Mode:**
```bash
python -m bazi_engine.cli 2024-02-10T14:30:00 \
  --tz Europe/Berlin \
  --lon 13.405 \
  --lat 52.52

# With JSON output
python -m bazi_engine.cli 2024-02-10T14:30:00 \
  --tz Europe/Berlin \
  --lon 13.405 \
  --lat 52.52 \
  --json

# With LMT and Zi boundary
python -m bazi_engine.cli 2024-02-10T14:30:00 \
  --tz Europe/Berlin \
  --lon 13.405 \
  --lat 52.52 \
  --standard LMT \
  --boundary zi
```

**API Server:**
```bash
# Start FastAPI server
uvicorn bazi_engine.app:app --host 0.0.0.0 --port 8080

# With auto-reload for development
uvicorn bazi_engine.app:app --reload

# Access API docs
# Navigate to: http://localhost:8080/docs
```

**Docker:**
```bash
# Build the image
docker build -t bazi_engine .

# Run the container
docker run -p 8080:8080 bazi_engine

# Test endpoint
curl http://localhost:8080/health
```

### Testing Strategy

**Three test categories:**

1. **Golden Vectors** (`tests/test_golden.py`) - Known correct results
   - 4 parametrized test cases
   - Exact pillar expectations
   - Edge cases: pre/post LiChun, LMT+Zi boundary

2. **Extended Vectors** (`tests/test_golden_vectors.py`) - Additional coverage
   - High latitude (78°N Longyearbyen)
   - Custom day anchors (future v0.4)
   - Configuration variations

3. **Invariants** (`tests/test_invariants.py`) - Structural validation
   - Month boundaries strictly increasing
   - Reference date validation (DAY_OFFSET calibration)

**Running tests:**
```bash
pytest -q                           # Quick run
pytest -v                           # Verbose output
pytest tests/test_golden.py         # Specific file
pytest -k "test_day_offset"         # Pattern matching
pytest --tb=short                   # Short traceback
```

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/ci.yml`):
- **Triggers**: Push to main branch, all pull requests to main
- **Matrix**: Python 3.10, 3.11 on ubuntu-latest
- **Steps**:
  1. Checkout code
  2. Set up Python versions
  3. Install dependencies + Swiss Ephemeris system libraries
  4. Download ephemeris data files (1800-2400 AD)
  5. Run pytest with verbose output

**Environment**: `SE_EPHE_PATH=/usr/local/share/swisseph`

---

## KEY CONVENTIONS

### Code Style

- **Naming Conventions**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes and dataclasses
  - `UPPERCASE` for constants (STEMS, BRANCHES, DAY_OFFSET)

- **Type Hints**:
  - Complete coverage throughout codebase
  - Use `from __future__ import annotations` for forward references
  - Type aliases: `TimeStandard`, `DayBoundary`, `Fold`

- **Imports**:
  - Organized in three groups: stdlib → third-party → local
  - Example:
    ```python
    from __future__ import annotations

    from datetime import datetime
    from typing import Optional

    import swisseph as swe

    from .types import BaziInput, BaziResult
    from .constants import STEMS, BRANCHES
    ```

- **Docstrings**:
  - Module-level docstrings in `__init__.py`
  - Minimal inline comments (code should be self-documenting)
  - Key algorithm comments where complexity is high

### Design Patterns

1. **Functional Programming**
   - Pure functions (no side effects)
   - Immutable data structures (frozen=True)
   - Function composition for calculation pipelines
   - No global state modifications

2. **Protocol Pattern** (bazi_engine/ephemeris.py)
   ```python
   class EphemerisBackend(Protocol):
       """Interface for pluggable ephemeris backends."""
       def delta_t_seconds(self, jd_ut: float) -> float: ...
       def sun_lon_deg_ut(self, jd_ut: float) -> float: ...
       def solcross_ut(self, target_lon_deg: float, jd_start_ut: float) -> float: ...
   ```
   - Enables future Skyfield integration
   - Testable backend abstraction

3. **Bisection Algorithm** (bazi_engine/jieqi.py:42)
   - Generic solar longitude crossing finder
   - Fallback when `solcross_ut()` unavailable
   - Configurable accuracy (default: 1 second)
   - Example:
     ```python
     def find_crossing(
         backend: EphemerisBackend,
         target_lon_deg: float,
         jd_start_ut: float,
         *,
         accuracy_seconds: float,
         max_span_days: float = 40.0,
     ) -> float:
         # Generic bisection implementation
     ```

### Error Handling

- **LocalTimeError** (bazi_engine/time_utils.py):
  - Raised for nonexistent DST times (spring forward)
  - Raised for ambiguous DST times (fall back) when strict=True

- **HTTPException** (bazi_engine/app.py):
  - FastAPI endpoint errors
  - 400 for invalid input
  - 500 for calculation errors

- **NotImplementedError**:
  - Skyfield backend (stub only in v0.2)
  - Future features marked in types.py (v0.4)

- **Try-catch for diagnostics**:
  - Solar terms computation wrapped in try-catch
  - Non-critical, doesn't fail main calculation

### Git Workflow

**Current Branch**: `claude/add-claude-documentation-lTBjN`

**Branch Naming Convention**: `claude/<description>-<session-id>`
- Feature branches for all development
- Pull requests for merges to main
- Clean, descriptive commit messages

**Commit Style**:
- Descriptive messages focusing on "what" and "why"
- Examples from history:
  - "Add comprehensive performance analysis and benchmarking"
  - "Add comprehensive German architecture documentation"
  - "Add Python .gitignore to exclude cache and build artifacts"
- Semantic prefixes: "Add", "Update", "Fix", "Refactor", "Merge pull request"

**Git Commands for Development**:
```bash
# Check current branch
git status

# Create new branch (if needed)
git checkout -b claude/feature-name-<session-id>

# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature X to improve Y"

# Push to remote (with retry logic for network errors)
git push -u origin claude/add-claude-documentation-lTBjN
```

---

## COMMON TASKS FOR AI ASSISTANTS

### 1. Adding New Features

**Before modifying code:**
- ✓ Read relevant files first (NEVER propose changes without reading)
- ✓ Understand existing patterns and conventions
- ✓ Check for similar implementations in codebase
- ✓ Review module dependencies to avoid circular imports

**Development Steps:**
1. Identify affected modules from dependency graph
2. Read existing code in those modules
3. Write test cases first (golden vectors if possible)
4. Implement feature following functional patterns
5. Ensure immutability (frozen dataclasses)
6. Add complete type hints
7. Run tests: `pytest -v`
8. Update documentation if public API changes

**Example: Adding a new configuration option**

```python
# Step 1: Update types.py
@dataclass(frozen=True)
class BaziInput:
    # ... existing fields ...
    new_option: bool = False  # Add new field with default

# Step 2: Update bazi.py to use new option
def compute_bazi(inp: BaziInput) -> BaziResult:
    # ... existing code ...
    if inp.new_option:
        # Implement new behavior
        pass

# Step 3: Add test in test_golden_vectors.py
("test_new_option",
 BaziInput(..., new_option=True),
 ("ExpectedYear", "ExpectedMonth", "ExpectedDay", "ExpectedHour"))

# Step 4: Run tests
pytest -v

# Step 5: Update app.py for API support
class BaziRequest(BaseModel):
    # ... existing fields ...
    new_option: bool = False
```

### 2. Debugging Calculation Issues

**Diagnostic Tools:**

1. **Enable 24 Solar Terms** (diagnostic mode):
   ```python
   result = compute_bazi(BaziInput(...))
   if result.solar_terms_local_dt:
       for term in result.solar_terms_local_dt:
           print(f"Term {term.index}: {term.target_lon_deg}° at {term.local_dt}")
   ```

2. **Inspect BaziResult fields**:
   ```python
   result = compute_bazi(inp)
   print(f"JD UT: {result.jd_ut}")
   print(f"JD TT: {result.jd_tt}")
   print(f"ΔT: {result.delta_t_seconds}s")
   print(f"Birth local: {result.birth_local_dt}")
   print(f"Birth UTC: {result.birth_utc_dt}")
   print(f"Chart local: {result.chart_local_dt}")
   print(f"LiChun: {result.lichun_local_dt}")
   print(f"Month index: {result.month_index}")
   ```

3. **Check Month Boundaries**:
   ```python
   for i, boundary in enumerate(result.month_boundaries_local_dt):
       print(f"Month {i}: {boundary}")
   ```

4. **Compare with Golden Vectors**:
   ```python
   from tests.test_golden import GOLDEN_CASES

   for name, inp, expected in GOLDEN_CASES:
       result = compute_bazi(inp)
       pillars = (
           str(result.pillars.year),
           str(result.pillars.month),
           str(result.pillars.day),
           str(result.pillars.hour),
       )
       if pillars != expected:
           print(f"❌ {name}: got {pillars}, expected {expected}")
       else:
           print(f"✓ {name}")
   ```

**Common Issues:**

- **DST Transitions**: Use `strict_local_time=False` or specify `fold`
- **Month Boundaries**: Verify Jie crossing calculations
- **Day Pillar**: Check JDN calculation with `DAY_OFFSET=49`
- **High Latitudes**: May have extreme solar term timings
- **LiChun Edge Case**: Birth before/after LiChun affects year pillar

### 3. Performance Optimization

**Current Performance** (from PERFORMANCE_ANALYSIS_DE.md):
- ~30ms average response time
- ~15-25ms without solar terms computation
- ~50-100ms with 24 solar terms
- ~200 MB memory (dependencies + ephemeris data)
- ~20-50 requests/second per instance capacity

**Optimization Targets:**

1. **Caching Solar Term Crossings**:
   - Most expensive operation (~10-50ms)
   - Cache common date ranges
   - Implement in ephemeris.py

2. **Batch Processing**:
   - Vectorize multiple calculations
   - Reuse ephemeris backend across requests

3. **Ephemeris Pre-loading**:
   - Pre-load commonly used date ranges
   - Reduce Swiss Ephemeris file I/O

4. **FastAPI Middleware**:
   - Response caching for identical requests
   - Compression for large responses

**Benchmark Script:**
```bash
python benchmark_performance.py
```

**Example output**:
```
Single request: 28.5ms
100 sequential requests: 2.85s (35.09 req/s)
Memory usage: 198 MB
Estimated capacity: 23 concurrent users
```

### 4. Adding Tests

**Golden Vector Template:**

```python
# tests/test_golden.py or tests/test_golden_vectors.py

GOLDEN_CASES = [
    (
        "descriptive_test_name",
        BaziInput(
            birth_local="2024-02-10T14:30:00",
            timezone="Europe/Berlin",
            longitude_deg=13.4050,
            latitude_deg=52.52,
            # Optional parameters
            time_standard="CIVIL",
            day_boundary="midnight",
            strict_local_time=True,
            fold=0,
        ),
        ("YearPillar", "MonthPillar", "DayPillar", "HourPillar"),
    ),
]

@pytest.mark.parametrize("name,inp,expected", GOLDEN_CASES)
def test_golden_cases(name, inp, expected):
    result = compute_bazi(inp)
    pillars = (
        str(result.pillars.year),
        str(result.pillars.month),
        str(result.pillars.day),
        str(result.pillars.hour),
    )
    assert pillars == expected, f"{name} failed"
```

**Invariant Test Template:**

```python
# tests/test_invariants.py

def test_month_boundaries_strictly_increasing():
    """Verify that all 13 month boundaries are in strictly increasing order."""
    inp = BaziInput(
        birth_local="2024-02-10T14:30:00",
        timezone="Europe/Berlin",
        longitude_deg=13.4050,
        latitude_deg=52.52,
    )
    result = compute_bazi(inp)

    boundaries = result.month_boundaries_local_dt
    assert len(boundaries) == 13

    for i in range(len(boundaries) - 1):
        assert boundaries[i] < boundaries[i + 1], \
            f"Boundary {i} not < boundary {i+1}"
```

### 5. API Endpoint Development

**FastAPI Patterns** (bazi_engine/app.py):

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class BaziRequest(BaseModel):
    date: str
    timezone: str
    longitude: float
    latitude: float
    time_standard: str = "CIVIL"
    day_boundary: str = "midnight"
    strict_local_time: bool = True
    fold: int = 0

class BaziResponse(BaseModel):
    pillars: dict
    birth_local: str
    birth_utc: str
    # ... more fields

@app.post("/calculate/bazi", response_model=BaziResponse)
async def calculate_bazi_endpoint(req: BaziRequest):
    try:
        # Map request to BaziInput
        inp = BaziInput(
            birth_local=req.date,
            timezone=req.timezone,
            longitude_deg=req.longitude,
            latitude_deg=req.latitude,
            time_standard=req.time_standard,
            day_boundary=req.day_boundary,
            strict_local_time=req.strict_local_time,
            fold=req.fold,
        )

        # Compute result
        result = compute_bazi(inp)

        # Map result to response
        return BaziResponse(
            pillars={
                "year": {"stem": STEMS[result.pillars.year.stem_index], ...},
                # ... more fields
            },
            birth_local=result.birth_local_dt.isoformat(),
            birth_utc=result.birth_utc_dt.isoformat(),
            # ... more fields
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Testing Endpoints:**

```bash
# Using curl
curl -X POST http://localhost:8080/calculate/bazi \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-02-10T14:30:00",
    "timezone": "Europe/Berlin",
    "longitude": 13.4050,
    "latitude": 52.52
  }'

# Using httpie (if installed)
http POST http://localhost:8080/calculate/bazi \
  date="2024-02-10T14:30:00" \
  timezone="Europe/Berlin" \
  longitude:=13.4050 \
  latitude:=52.52

# Using Python requests
import requests
response = requests.post(
    "http://localhost:8080/calculate/bazi",
    json={
        "date": "2024-02-10T14:30:00",
        "timezone": "Europe/Berlin",
        "longitude": 13.4050,
        "latitude": 52.52,
    }
)
print(response.json())
```

---

## IMPORTANT GOTCHAS

### 1. Swiss Ephemeris Data Files

**Required Files**: sepl_18.se1, semo_18.se1, seplm06.se1 (covers 1800-2400 AD)

**Default Path**: `/usr/local/share/swisseph`

**Custom Path**: Via `ephe_path` parameter or `SE_EPHE_PATH` environment variable

**Error if Missing**: `SwissEph file '...' not found`

**Solution:**
```bash
# Download ephemeris files
mkdir -p /usr/local/share/swisseph
cd /usr/local/share/swisseph

# Download from astro.com FTP
wget https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1
wget https://www.astro.com/ftp/swisseph/ephe/semo_18.se1
wget https://www.astro.com/ftp/swisseph/ephe/seplm06.se1

# Or set custom path
export SE_EPHE_PATH=/custom/path

# Or in BaziInput
result = compute_bazi(BaziInput(..., ephe_path="/custom/path"))
```

**Dockerfile**: Already handles this in multi-stage build

**CI Pipeline**: Downloads files in GitHub Actions workflow

### 2. DST (Daylight Saving Time) Handling

**Nonexistent Times** (spring forward):
```python
# 2024-03-31T02:30:00 doesn't exist in Europe/Berlin
# Clock jumps from 02:00 to 03:00

# This will raise LocalTimeError with strict=True
BaziInput(
    birth_local="2024-03-31T02:30:00",
    timezone="Europe/Berlin",
    strict_local_time=True,  # ❌ Raises LocalTimeError
)

# Solution 1: Use lenient mode
BaziInput(
    birth_local="2024-03-31T02:30:00",
    timezone="Europe/Berlin",
    strict_local_time=False,  # ✓ Works (interprets as post-transition)
)

# Solution 2: Use valid time
BaziInput(
    birth_local="2024-03-31T03:30:00",  # After transition
    timezone="Europe/Berlin",
)
```

**Ambiguous Times** (fall back):
```python
# 2024-10-27T02:30:00 occurs twice in Europe/Berlin
# Clock rolls back from 03:00 to 02:00

# Must specify fold parameter
BaziInput(
    birth_local="2024-10-27T02:30:00",
    timezone="Europe/Berlin",
    fold=0,  # First occurrence (DST, UTC+2)
)

BaziInput(
    birth_local="2024-10-27T02:30:00",
    timezone="Europe/Berlin",
    fold=1,  # Second occurrence (standard time, UTC+1)
)

# Without fold specification, default is fold=0
```

**Best Practices**:
- Always handle `LocalTimeError` in API endpoints
- Document DST behavior for users
- Test with DST transition dates
- Consider timezone-aware datetime libraries

### 3. LiChun Year Boundary

**Critical Edge Case**: Birth before LiChun uses previous year's pillar

**LiChun** (Start of Spring):
- Occurs at 315° solar longitude
- Typically around February 3-5 (varies by year)
- Timezone matters: Berlin LiChun ≠ Beijing LiChun

**Example** (`bazi_engine/bazi.py`:69–74):
```python
# 2024-02-04T09:26:00 Berlin (BEFORE LiChun at 09:27)
solar_year = 2023  # GuiMao year (2023)
year_pillar = year_pillar_from_solar_year(2023)  # GuiMao

# 2024-02-04T09:28:00 Berlin (AFTER LiChun at 09:27)
solar_year = 2024  # JiaChen year (2024)
year_pillar = year_pillar_from_solar_year(2024)  # JiaChen
```

**Testing**: See `tests/test_golden.py` cases for pre/post LiChun

**Debugging**:
```python
result = compute_bazi(inp)
print(f"LiChun: {result.lichun_local_dt}")
print(f"Birth: {result.birth_local_dt}")
print(f"Before LiChun: {result.birth_local_dt < result.lichun_local_dt}")
```

### 4. Day Offset Constant

**DAY_OFFSET = 49** (bazi_engine/constants.py:6)

**Purpose**: Calibration constant for JDN → sexagenary day cycle alignment

**Critical**: Ensures day pillar accuracy

**DO NOT MODIFY** unless:
- Recalibrating with known reference dates
- Using different reference system
- Have multiple golden vectors to validate

**Formula** (bazi_engine/bazi.py:19):
```python
def sexagenary_day_index_from_date(y: int, m: int, d: int, offset: int = DAY_OFFSET) -> int:
    return (jdn_gregorian(y, m, d) + offset) % 60
```

**Validation**: `tests/test_invariants.py::test_day_offset_reference_examples`

**Historical Context**:
- Reference date: 1949-10-01 as Jia-Zi day
- Offset derived from Julian Day Number calibration
- Consistent across all astronomical almanacs

### 5. Immutability Requirement

**All dataclasses are frozen**:

```python
@dataclass(frozen=True)
class Pillar:
    stem_index: int
    branch_index: int

# Cannot modify after creation
p = Pillar(0, 0)
p.stem_index = 1  # ❌ Raises FrozenInstanceError
```

**Why Immutability?**
- Ensures deterministic calculations
- Prevents accidental mutations
- Enables safe caching (future)
- Thread-safe by design
- Functional programming paradigm

**Workaround** (create new instance):
```python
# Instead of modifying
p = Pillar(0, 0)
# p.stem_index = 1  # ❌ Not allowed

# Create new instance
p = Pillar(1, 0)  # ✓ Correct approach
```

**In Functions**:
```python
# Don't try to modify input
def compute_bazi(inp: BaziInput) -> BaziResult:
    # inp.birth_local = "..."  # ❌ Will fail

    # Instead, create new BaziInput if needed
    modified_inp = BaziInput(
        birth_local="...",
        timezone=inp.timezone,
        longitude_deg=inp.longitude_deg,
        latitude_deg=inp.latitude_deg,
    )
```

### 6. Module Circular Import Prevention

**Dependency Hierarchy** (must be respected):

```
Level 0: constants.py (no dependencies)
Level 1: types.py (depends on constants.py)
Level 2: ephemeris.py, time_utils.py (depend on types.py)
Level 3: jieqi.py (depends on ephemeris.py)
Level 4: bazi.py (depends on jieqi.py, time_utils.py, ephemeris.py)
Level 5: app.py, cli.py, western.py (depend on bazi.py)
```

**Rules**:
- Lower-level modules CANNOT import higher-level modules
- `bazi.py` CANNOT be imported by ephemeris.py, jieqi.py, time_utils.py
- If you need shared code, put it in a lower-level module

**Example of Circular Import Error**:
```python
# ❌ WRONG - causes circular import
# In ephemeris.py
from .bazi import compute_bazi  # ERROR!

# ✓ CORRECT - move shared code to types.py or create new module
# In shared_utils.py (new file)
def shared_function():
    pass

# In ephemeris.py
from .shared_utils import shared_function

# In bazi.py
from .shared_utils import shared_function
```

---

## FILE REFERENCE

### Core Calculation Files

| File | Purpose | Key Functions/Classes | LOC |
|------|---------|----------------------|-----|
| `bazi_engine/bazi.py` | Main calculation engine | `compute_bazi()` (line 45), `year_pillar_from_solar_year()`, `month_pillar_from_year_stem()`, `hour_pillar_from_day_stem()` | 149 |
| `bazi_engine/types.py` | Data structures | `Pillar`, `FourPillars`, `BaziInput`, `BaziResult`, `SolarTerm` | 75 |
| `bazi_engine/constants.py` | Domain constants | `STEMS`, `BRANCHES`, `DAY_OFFSET` | 6 |
| `bazi_engine/ephemeris.py` | Swiss Ephemeris backend | `SwissEphBackend`, `EphemerisBackend` protocol, `datetime_utc_to_jd_ut()` | 70 |
| `bazi_engine/jieqi.py` | Solar term calculations | `find_crossing()`, `compute_month_boundaries_from_lichun()`, `compute_24_solar_terms_for_window()` | 98 |
| `bazi_engine/time_utils.py` | Time handling | `parse_local_iso()`, `to_chart_local()`, `apply_day_boundary()`, `LocalTimeError` | 41 |

### API and Interface Files

| File | Purpose | Key Elements | LOC |
|------|---------|--------------|-----|
| `bazi_engine/app.py` | FastAPI REST API | `POST /calculate/bazi`, `POST /calculate/western`, `BaziRequest`, `BaziResponse` | 106 |
| `bazi_engine/cli.py` | Command-line interface | `main()`, argument parsing | 66 |
| `bazi_engine/western.py` | Western astrology | `compute_western_chart()`, planetary positions, house calculations | 120 |
| `bazi_engine/__init__.py` | Package exports | Public API surface | 15 |

### Test Files

| File | Purpose | Test Count |
|------|---------|------------|
| `tests/test_golden.py` | Golden vector tests with known correct results | 4 parametrized cases |
| `tests/test_golden_vectors.py` | Extended test vectors for edge cases | Multiple cases |
| `tests/test_invariants.py` | Structural invariant validation | 2 tests |

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package metadata, dependencies (pyswisseph, fastapi, uvicorn), build config |
| `Dockerfile` | Multi-stage Docker build with Swiss Ephemeris setup, exposes port 8080 |
| `fly.toml` | Fly.io deployment config (1GB RAM, Frankfurt region, auto-scaling) |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline (Python 3.10-3.11 matrix, pytest) |
| `.gitignore` | Standard Python exclusions (\_\_pycache\_\_, .venv, .coverage, IDE files) |

### Documentation Files

| File | Language | Purpose | Size |
|------|----------|---------|------|
| `README.md` | English | Quick start guide and feature overview | 1KB |
| `QWEN.md` | English | AI assistant development context (Qwen-specific) | 5KB |
| `ARCHITECTURE_DE.md` | German | Comprehensive architecture documentation with algorithms | 36KB |
| `PERFORMANCE_ANALYSIS_DE.md` | German | Performance benchmarks and scaling recommendations | 11KB |
| `CLAUDE.md` | English | **This file** - Claude assistant comprehensive guide | Current |

---

## API REFERENCE

### REST API Endpoints

**Base URL**: `http://localhost:8080`

**Health Check**:
- `GET /` - Returns "OK"
- `GET /health` - Returns health status

#### POST /calculate/bazi

Calculate BaZi (Four Pillars) chart based on birth datetime and location.

**Request Body** (BaziRequest):
```json
{
  "date": "2024-02-10T14:30:00",
  "timezone": "Europe/Berlin",
  "longitude": 13.4050,
  "latitude": 52.52,
  "time_standard": "CIVIL",
  "day_boundary": "midnight",
  "strict_local_time": true,
  "fold": 0
}
```

**Response** (BaziResponse):
```json
{
  "pillars": {
    "year": {"stem": "Jia", "branch": "Chen"},
    "month": {"stem": "Bing", "branch": "Yin"},
    "day": {"stem": "Jia", "branch": "Chen"},
    "hour": {"stem": "Xin", "branch": "Wei"}
  },
  "birth_local": "2024-02-10T14:30:00",
  "birth_utc": "2024-02-10T13:30:00Z",
  "chart_local": "2024-02-10T14:30:00",
  "jd_ut": 2460351.0625,
  "jd_tt": 2460351.0633,
  "delta_t_seconds": 69.184,
  "lichun_local": "2024-02-04T09:27:00",
  "month_boundaries": ["2024-02-04T09:27:00", ...],
  "month_index": 0
}
```

**Error Response** (400):
```json
{
  "detail": "Error message here"
}
```

#### POST /calculate/western

Calculate Western astrology chart (planets, houses, angles).

**Request Body** (WesternRequest):
```json
{
  "date": "2024-02-10T14:30:00",
  "timezone": "Europe/Berlin",
  "longitude": 13.4050,
  "latitude": 52.52
}
```

**Response** (WesternChartResponse):
```json
{
  "jd": 2460351.0625,
  "planets": {
    "Sun": {"longitude": 321.5, "latitude": 0.0, "retrograde": false},
    "Moon": {"longitude": 45.2, "latitude": 1.3, "retrograde": false},
    "Mercury": {"longitude": 280.1, "latitude": -2.1, "retrograde": true},
    ...
  },
  "houses": [0.0, 30.0, 60.0, ...],
  "angles": {
    "asc": 120.5,
    "mc": 210.3,
    "vertex": 45.2
  }
}
```

### Command-Line Interface

```bash
python -m bazi_engine.cli <LOCAL_ISO_DATE> [OPTIONS]

Arguments:
  LOCAL_ISO_DATE     Birth date and time in ISO 8601 format
                     Example: 2024-02-10T14:30:00

Options:
  --tz TIMEZONE            IANA timezone name (default: Europe/Berlin)
  --lon DEGREES            Longitude in degrees (default: 13.4050)
  --lat DEGREES            Latitude in degrees (default: 52.52)
  --standard {CIVIL,LMT}   Time standard (default: CIVIL)
  --boundary {midnight,zi} Day boundary (default: midnight)
  --json                   Output JSON format instead of human-readable
  --help                   Show help message

Examples:
  # Basic usage
  python -m bazi_engine.cli 2024-02-10T14:30:00

  # With all options
  python -m bazi_engine.cli 2024-02-10T14:30:00 \
    --tz Europe/Berlin \
    --lon 13.405 \
    --lat 52.52 \
    --standard CIVIL \
    --boundary midnight

  # JSON output
  python -m bazi_engine.cli 2024-02-10T14:30:00 --json
```

---

## DEBUGGING TIPS

### 1. Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Swiss Ephemeris internal logging (if available)
import swisseph as swe
swe.set_ephe_path("/usr/local/share/swisseph")
```

### 2. Use Diagnostic Solar Terms

```python
# Enable 24 solar terms computation for debugging
inp = BaziInput(
    birth_local="2024-02-10T14:30:00",
    timezone="Europe/Berlin",
    longitude_deg=13.4050,
    latitude_deg=52.52,
)

result = compute_bazi(inp)

# Inspect solar terms
if result.solar_terms_local_dt:
    print("24 Solar Terms:")
    for term in result.solar_terms_local_dt:
        print(f"  {term.index:2d}: {term.target_lon_deg:6.1f}° at {term.local_dt}")
```

### 3. Inspect Intermediate Calculation Values

```python
result = compute_bazi(inp)

print("=== Time Conversions ===")
print(f"Birth local: {result.birth_local_dt}")
print(f"Birth UTC:   {result.birth_utc_dt}")
print(f"Chart local: {result.chart_local_dt}")

print("\n=== Julian Days ===")
print(f"JD UT: {result.jd_ut}")
print(f"JD TT: {result.jd_tt}")
print(f"ΔT:    {result.delta_t_seconds:.3f} seconds")

print("\n=== Year Boundary ===")
print(f"LiChun: {result.lichun_local_dt}")
print(f"Birth is {'BEFORE' if result.birth_local_dt < result.lichun_local_dt else 'AFTER'} LiChun")

print("\n=== Month Boundaries ===")
for i, boundary in enumerate(result.month_boundaries_local_dt):
    marker = " <-- birth" if i == result.month_index else ""
    print(f"Month {i:2d}: {boundary}{marker}")

print("\n=== Pillars ===")
print(f"Year:  {result.pillars.year}  (stem={result.pillars.year.stem_index}, branch={result.pillars.year.branch_index})")
print(f"Month: {result.pillars.month} (stem={result.pillars.month.stem_index}, branch={result.pillars.month.branch_index})")
print(f"Day:   {result.pillars.day}   (stem={result.pillars.day.stem_index}, branch={result.pillars.day.branch_index})")
print(f"Hour:  {result.pillars.hour}  (stem={result.pillars.hour.stem_index}, branch={result.pillars.hour.branch_index})")
```

### 4. Compare with Golden Vectors

```python
from tests.test_golden import GOLDEN_CASES

print("=== Golden Vector Validation ===")
for name, inp, expected in GOLDEN_CASES:
    result = compute_bazi(inp)
    pillars = (
        str(result.pillars.year),
        str(result.pillars.month),
        str(result.pillars.day),
        str(result.pillars.hour),
    )
    status = "✓" if pillars == expected else "❌"
    print(f"{status} {name}")
    if pillars != expected:
        print(f"  Expected: {expected}")
        print(f"  Got:      {pillars}")
```

### 5. Test Swiss Ephemeris Installation

```python
import swisseph as swe

# Check ephemeris path
print(f"Ephemeris path: {swe.get_library_path()}")

# Test Sun position calculation
jd = swe.julday(2024, 2, 10, 14.5)
sun_lon, _ = swe.calc_ut(jd, swe.SUN)
print(f"Sun longitude at JD {jd}: {sun_lon[0]:.2f}°")

# Test solcross_ut
lichun_jd = swe.solcross_ut(315.0, swe.julday(2024, 1, 1, 0.0), 0)
print(f"LiChun 2024 JD: {lichun_jd}")
```

### 6. Validate Timezone Handling

```python
from zoneinfo import ZoneInfo
from datetime import datetime

# Test timezone conversion
tz = ZoneInfo("Europe/Berlin")
dt_local = datetime(2024, 2, 10, 14, 30, 0, tzinfo=tz)
dt_utc = dt_local.astimezone(ZoneInfo("UTC"))

print(f"Local: {dt_local}")
print(f"UTC:   {dt_utc}")
print(f"Offset: {dt_local.utcoffset()}")

# Test DST transitions
dst_spring = datetime(2024, 3, 31, 2, 30, 0)  # Nonexistent (in some tz rules)
dst_fall = datetime(2024, 10, 27, 2, 30, 0)    # Ambiguous

# With zoneinfo, make the naive time "aware" via replace(tzinfo=...)
dst_spring_aware = dst_spring.replace(tzinfo=tz)
print(f"Spring forward (aware): {dst_spring_aware} UTC offset {dst_spring_aware.utcoffset()}")

# Use fold parameter for ambiguous times
dt_fall_0 = datetime(2024, 10, 27, 2, 30, 0, fold=0, tzinfo=tz)
dt_fall_1 = datetime(2024, 10, 27, 2, 30, 0, fold=1, tzinfo=tz)
print(f"Fall back (fold=0): {dt_fall_0} UTC offset {dt_fall_0.utcoffset()}")
print(f"Fall back (fold=1): {dt_fall_1} UTC offset {dt_fall_1.utcoffset()}")
```

---

## DEPLOYMENT

### Docker Build and Run

```bash
# Build the Docker image
docker build -t bazi_engine .

# Run the container
docker run -p 8080:8080 bazi_engine

# Run with custom ephemeris path
docker run -p 8080:8080 \
  -v /path/to/ephemeris:/usr/local/share/swisseph \
  -e SE_EPHE_PATH=/usr/local/share/swisseph \
  bazi_engine

# Run in detached mode
docker run -d -p 8080:8080 --name bazi_engine bazi_engine

# View logs
docker logs bazi_engine

# Stop container
docker stop bazi_engine

# Test endpoint
curl http://localhost:8080/health
```

### Fly.io Deployment

```bash
# Install flyctl (if not already installed)
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
flyctl auth login

# Deploy application (first time)
flyctl launch

# Subsequent deploys
flyctl deploy

# Check deployment status
flyctl status

# View live logs
flyctl logs

# Scale resources
flyctl scale memory 2048  # 2GB RAM
flyctl scale count 2      # 2 instances

# Open in browser
flyctl open

# SSH into instance
flyctl ssh console
```

**Configuration** (fly.toml):
```toml
app = "bazi-engine"
primary_region = "fra"  # Frankfurt

[build]
  dockerfile = "Dockerfile"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 1024
```

### Performance Monitoring

```bash
# Fly.io metrics
flyctl metrics

# Docker container stats
docker stats bazi_engine

# HTTP load testing (with hey)
hey -n 1000 -c 10 -m POST -H "Content-Type: application/json" \
  -d '{"date":"2024-02-10T14:30:00","timezone":"Europe/Berlin","longitude":13.405,"latitude":52.52}' \
  http://localhost:8080/calculate/bazi

# Or use the benchmark script
python benchmark_performance.py
```

---

## FUTURE ROADMAP

### Version 0.4 Planned Features

From `bazi_engine/types.py:51-56`, these fields are already defined but not implemented:

1. **Configurable Day Anchor**
   ```python
   day_anchor_date_iso: Optional[str] = None       # e.g., "1949-10-01"
   day_anchor_pillar_idx: Optional[int] = None     # e.g., 0 for JiaZi
   ```
   - Custom reference dates for day pillar calibration
   - Enables verification against different systems
   - Currently hardcoded with DAY_OFFSET=49

2. **Alternative Month Boundary Schemes**
   ```python
   month_boundary_scheme: Literal["jie_only", "all_24"] = "jie_only"
   ```
   - Support for different traditional approaches
   - "jie_only": Current implementation (12 Jie terms)
   - "all_24": Use all 24 solar terms for month boundaries

3. **Skyfield Backend Implementation**
   - Complete `SkyFieldBackend` implementation (currently stub)
   - Alternative to Swiss Ephemeris
   - Pure Python solution
   - May have different performance characteristics

4. **Caching Layer**
   - Cache solar term crossings for common date ranges
   - Significant performance improvement (50-80% faster)
   - LRU cache for ephemeris queries
   - Configurable cache size

### Potential Future Enhancements

- **Batch Calculation API**: Calculate multiple charts in one request
- **WebSocket Support**: Real-time chart updates
- **Database Integration**: Store and retrieve charts
- **User Authentication**: Multi-user support
- **Chart Comparison**: Compare two or more charts
- **Export Formats**: PDF, PNG chart visualizations
- **Internationalization**: Multi-language support (currently English/German)
- **Mobile App Integration**: REST API already mobile-friendly

---

## QUICK REFERENCE CHEAT SHEET

### Most Important Files
- **Main entry point**: `bazi_engine/bazi.py:46` (`compute_bazi()`)
- **Data types**: `bazi_engine/types.py`
- **Constants**: `bazi_engine/constants.py` (STEMS, BRANCHES, DAY_OFFSET=49)
- **Tests**: `tests/test_golden.py`, `tests/test_invariants.py`
- **API**: `bazi_engine/app.py`

### Most Important Commands
```bash
# Development
pip install -e ".[dev]"           # Install with dev dependencies
pytest -v                          # Run all tests with verbose output
pytest -k "test_name"              # Run specific test
python -m bazi_engine.cli ...     # CLI usage

# Running
uvicorn bazi_engine.app:app --reload  # Start API with auto-reload
python -m bazi_engine.cli 2024-02-10T14:30:00 --json  # CLI JSON output

# Testing
pytest -q                          # Quick test run
pytest tests/test_golden.py -v    # Specific test file
python benchmark_performance.py    # Performance benchmarking

# Docker
docker build -t bazi_engine .     # Build container
docker run -p 8080:8080 bazi_engine  # Run container

# Deployment
flyctl deploy                      # Deploy to Fly.io
flyctl logs                        # View logs
```

### Most Important Concepts
1. **Immutability**: All dataclasses frozen (frozen=True)
2. **Determinism**: Pure functions, no randomness, reproducible results
3. **LiChun Boundary**: Year changes at 315° solar longitude (~Feb 3-5)
4. **JDN + DAY_OFFSET**: Day pillar calculation (offset=49)
5. **12 Jie Terms**: Month boundaries (315°, 345°, 15°, 45°, ...)
6. **DST Handling**: Strict validation or lenient mode with fold parameter
7. **Golden Vectors**: Test-first with known correct results
8. **Type Safety**: Complete type hint coverage (Python 3.10+)

### Quick Debugging Checklist
- [ ] Swiss Ephemeris files downloaded? (`/usr/local/share/swisseph`)
- [ ] Timezone is valid IANA timezone? (e.g., "Europe/Berlin", not "CET")
- [ ] DST transition handled? (fold parameter for ambiguous times)
- [ ] LiChun boundary checked? (birth before/after affects year pillar)
- [ ] Tests passing? (`pytest -v`)
- [ ] Type hints complete? (mypy or pyright)
- [ ] Dataclasses frozen? (immutability enforced)
- [ ] Module imports correct? (no circular dependencies)

### Performance Targets
- Response time: ~30ms average (15-25ms without solar terms)
- Throughput: ~20-50 requests/second per instance
- Memory: ~200 MB (dependencies + ephemeris)
- Capacity: ~23 concurrent users per instance (1.5 req/user)

---

## BEST PRACTICES FOR AI ASSISTANTS

### DO ✓

1. **Always read files before modifying**
   - NEVER propose changes without reading the file first
   - Understand existing patterns and conventions

2. **Follow functional programming patterns**
   - Write pure functions (no side effects)
   - Use immutable data structures
   - Compose functions rather than mutating state

3. **Write tests first**
   - Add golden vectors for new features
   - Update existing tests when changing behavior
   - Ensure all tests pass before committing

4. **Respect type hints**
   - Add complete type hints to all new code
   - Use `from __future__ import annotations`
   - Run type checker if available (mypy, pyright)

5. **Maintain immutability**
   - Keep all dataclasses frozen
   - Create new instances instead of modifying
   - Preserve functional paradigm

6. **Document edge cases**
   - DST transitions
   - LiChun boundaries
   - High latitude locations
   - Month boundary edge cases

7. **Test thoroughly**
   - Golden vectors for correctness
   - Invariants for structural properties
   - Edge cases (DST, LiChun, high latitude)
   - Performance benchmarks

8. **Keep dependencies minimal**
   - Only add dependencies if truly necessary
   - Prefer stdlib solutions when possible
   - Document why new dependencies are needed

### DON'T ✗

1. **Don't modify without reading**
   - Never propose code changes without reading the file
   - Don't assume patterns without verifying

2. **Don't break immutability**
   - Never remove frozen=True from dataclasses
   - Don't introduce mutable state
   - Don't use global variables

3. **Don't skip tests**
   - Never commit without running tests
   - Don't assume tests still pass
   - Don't delete tests without good reason

4. **Don't create circular imports**
   - Respect module dependency hierarchy
   - Don't import higher-level modules from lower-level ones
   - Check dependency graph before importing

5. **Don't hardcode values**
   - Use constants from constants.py
   - Don't magic numbers without explanation
   - Don't duplicate constants

6. **Don't ignore DST**
   - Always handle LocalTimeError
   - Test with DST transition dates
   - Document DST behavior for users

7. **Don't modify DAY_OFFSET**
   - Unless recalibrating with golden vectors
   - Critical for day pillar accuracy
   - Tested in test_invariants.py

8. **Don't introduce randomness**
   - Keep calculations deterministic
   - No random seeds or probabilistic logic
   - Reproducibility is critical

---

## GETTING HELP

### Documentation Resources

1. **This File** (CLAUDE.md): Comprehensive guide for AI assistants
2. **README.md**: Quick start and feature overview
3. **QWEN.md**: Alternative AI assistant context
4. **ARCHITECTURE_DE.md**: Detailed German architecture documentation
5. **PERFORMANCE_ANALYSIS_DE.md**: Performance benchmarks and optimization

### Code Resources

1. **Tests**: `tests/test_golden.py` - Examples of correct usage
2. **CLI**: `bazi_engine/cli.py` - Command-line interface examples
3. **API**: `bazi_engine/app.py` - REST API endpoint examples
4. **Core Logic**: `bazi_engine/bazi.py` - Main calculation pipeline

### External Resources

1. **Swiss Ephemeris**: https://www.astro.com/swisseph/
2. **FastAPI**: https://fastapi.tiangolo.com/
3. **pytest**: https://docs.pytest.org/
4. **Python Type Hints**: https://docs.python.org/3/library/typing.html

---

## VERSION HISTORY

### v0.2.0 (Current)
- DST safety checks with strict/lenient modes
- Full 24 solar terms computation for diagnostics
- Ephemeris path injection for Swiss Ephemeris
- Skyfield adapter stub + generic bisection fallback
- Golden vectors + invariant tests
- Deterministic and test-first development

### v0.1.0 (MVP)
- Basic BaZi calculation (Year/Month/Day/Hour pillars)
- Swiss Ephemeris integration
- FastAPI REST API
- Command-line interface
- Docker containerization
- Fly.io deployment configuration

---

## CONCLUSION

This comprehensive guide provides AI assistants like Claude with all the necessary context to work effectively on the BaZi Engine codebase. When in doubt:

1. **Read the code first** - Never guess
2. **Follow existing patterns** - Consistency is key
3. **Write tests first** - Test-driven development
4. **Maintain immutability** - Frozen dataclasses
5. **Ensure determinism** - Pure functions
6. **Run tests before committing** - `pytest -v`

**Key Success Criteria**:
- ✓ All tests pass (`pytest -v`)
- ✓ Type hints complete
- ✓ Dataclasses remain frozen
- ✓ Functions remain pure
- ✓ No circular imports
- ✓ Documentation updated

Good luck working on the BaZi Engine! If you encounter issues not covered in this guide, consider updating this document for future AI assistants.

---

**Document Version**: 1.0
**Last Updated**: 2026-01-11
**Maintained For**: Claude and other AI assistants
**Repository**: BaZiEngine_v2
**Project Version**: 0.2.0
