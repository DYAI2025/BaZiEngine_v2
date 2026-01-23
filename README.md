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

## Webhook-Tool (HCI)
Methode: POST  
URL: https://baziengine-v2.fly.dev/calculate/bazi

Body (JSON):
```json
{
  "date": "{datum}",
  "tz": "Europe/Berlin",
  "lon": {lon},
  "lat": {lat}
}
```
Stelle sicher, dass `{datum}`, `{lon}` und `{lat}` aus dem User-Input kommen.

## GitHub Actions API (extern erreichbar)
Die BaZi Engine kann über GitHub Actions on-demand berechnet werden. Der Workflow liefert BaZi + Ephemeriden (westliche Planetenpositionen) als JSON im Workflow-Run Summary und als Artifact.

Workflow: `.github/workflows/bazi_engine_actions.yml`

### Auslösung via `workflow_dispatch`
Beispiel (GitHub REST API, benötigt `repo`-Token):

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <GITHUB_TOKEN>" \
  https://api.github.com/repos/<OWNER>/<REPO>/actions/workflows/bazi_engine_actions.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "date": "2024-02-10T14:30:00",
      "tz": "Europe/Berlin",
      "lon": "13.4050",
      "lat": "52.52",
      "standard": "CIVIL",
      "boundary": "midnight",
      "strict": "true"
    }
  }'
```

### Auslösung via `repository_dispatch`
```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <GITHUB_TOKEN>" \
  https://api.github.com/repos/<OWNER>/<REPO>/dispatches \
  -d '{
    "event_type": "bazi_engine",
    "client_payload": {
      "date": "2024-02-10T14:30:00",
      "tz": "Europe/Berlin",
      "lon": "13.4050",
      "lat": "52.52",
      "standard": "CIVIL",
      "boundary": "midnight",
      "strict": "true"
    }
  }'
```

### Ergebnis abrufen
* Workflow Summary enthält das JSON-Ergebnis.
* Artifact `bazi-engine-result` enthält `action_result.json`.
