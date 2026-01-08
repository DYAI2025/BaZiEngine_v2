# BaZi Engine v0.2 - Development Context

## Project Overview

BaZi Engine is an astronomical calculation engine for Chinese astrology (Four Pillars of Destiny) that uses precise astronomical calculations to determine birth chart pillars. The engine calculates the Year, Month, Day, and Hour pillars based on astronomical solar-term boundaries rather than simple calendar dates, ensuring accuracy according to traditional Chinese astrological principles.

Key features:
- Swiss Ephemeris (pyswisseph) for Sun apparent longitude and solstice calculations
- IANA timezone support with strict DST validation
- Optional Local Mean Time (LMT) calculation based on longitude
- Year boundary at LiChun (315° solar longitude)
- Month boundaries from exact Jie solar term crossings (315° + 30°*k)
- Day pillar from Julian Day Number (JDN) based sexagenary day index
- Hour pillar from 2-hour branches with optional Zi hour day-boundary
- Optional 24 solar terms computation for diagnostics and cross-validation

## Architecture

### Core Components
1. **bazi.py** - Main calculation logic for the BaZi chart
2. **types.py** - Data structures using TypedDict and dataclasses
3. **constants.py** - Heavenly Stems and Earthly Branches definitions
4. **time_utils.py** - Time parsing and conversion utilities
5. **ephemeris.py** - Swiss Ephemeris backend integration
6. **jieqi.py** - Solar term (Jie Qi) calculation logic
7. **cli.py** - Command-line interface
8. **app.py** - FastAPI web application
9. **western.py** - Western astrology calculation (complementary features)

### Data Flow
1. Input is parsed from local ISO date/time with timezone
2. Time is converted to UTC and then to chart-local time
3. Astronomical calculations determine exact solar term boundaries
4. Pillars are calculated based on position relative to these boundaries
5. Results include both the Four Pillars and diagnostic solar term information

## Building and Running

### Installation
```bash
# Install dependencies
pip install -e .

# For development with tests
pip install -e ".[dev]"
```

### Running the CLI
```bash
# Basic usage
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52

# With JSON output
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52 --json
```

### Running the Web API
```bash
# Start FastAPI server
uvicorn bazi_engine.app:app --host 0.0.0.0 --port 8080

# Or using the module approach
python -m bazi_engine.app
```

### Testing
```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_golden_vectors.py
```

### Docker Containerization
```bash
# Build the image
docker build -t bazi_engine .

# Run the container
docker run -p 8080:8080 bazi_engine
```

## Key Algorithms

### Year Pillar Calculation
- Uses LiChun (Start of Spring) at 315° solar longitude as the year boundary
- If birth date is before LiChun in the calendar year, the previous year's stem-branch is used
- Calculated using astronomical position rather than lunar calendar

### Month Pillar Calculation
- Uses Jie solar terms (12 of the 24 solar terms) as month boundaries
- Each month begins at its respective Jie term
- Formula: 315° + 30°*k where k = 0,1,2...11
- Month stem is derived from year stem using traditional formula

### Day Pillar Calculation
- Based on Julian Day Number converted to sexagenary cycle (60-day cycle)
- Uses configurable day anchor (default: 1949-10-01 as Jia-Zi day)
- Can be customized with different anchor dates for verification

### Hour Pillar Calculation
- Based on 2-hour time periods (Earthly Branches)
- Uses traditional Chinese hours (Zi, Chou, Yin, etc.)
- Hour stem derived from day stem using traditional formula

## Development Conventions

### Code Style
- Python 3.10+ with type hints
- Dataclasses for immutable data structures
- Functional approach to calculations
- Error handling with proper exceptions

### Testing Strategy
- Golden vector testing with known correct results
- Invariant validation to ensure consistent behavior
- Test-driven development approach
- Multiple test cases covering edge conditions

### Dependencies
- `pyswisseph` for astronomical calculations
- `fastapi` and `uvicorn` for web API
- `pytest` for testing
- `skyfield` (optional) as alternative ephemeris backend

## Version 0.2 Improvements

- DST safety checks for ambiguous/nonexistent local times (optional strict mode)
- Full 24 solar terms computation for a year window (UTC + chart-local)
- Caching hooks (extendable) + ephemeris path injection for Swiss Ephemeris
- Skyfield adapter stub (optional dependency) + generic bisection fallback solver
- Deterministic and test-first: golden vectors + invariants

## API Endpoints

- `GET /` - Health check
- `POST /calculate/bazi` - Calculate BaZi chart
- `POST /calculate/western` - Calculate Western astrology chart

## Configuration

The engine supports various options:
- Timezone validation with optional strict mode
- Choice between CIVIL and Local Mean Time (LMT)
- Day boundary options (midnight vs Zi hour)
- Custom day anchor for verification
- Accuracy settings for iterative calculations