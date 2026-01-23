from __future__ import annotations

from fastapi.testclient import TestClient

from bazi_engine.app import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_bazi_endpoint_success():
    payload = {
        "date": "2024-02-10T14:30:00",
        "tz": "Europe/Berlin",
        "lon": 13.405,
        "lat": 52.52,
        "standard": "CIVIL",
        "boundary": "midnight",
        "strict": True,
    }
    resp = client.post("/calculate/bazi", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pillars"]["year"] == {
        "stamm": "Jia",
        "zweig": "Chen",
        "tier": "Drache",
        "element": "Holz",
    }
    assert body["pillars"]["month"] == {
        "stamm": "Bing",
        "zweig": "Yin",
        "tier": "Tiger",
        "element": "Feuer",
    }
    assert body["pillars"]["day"] == {
        "stamm": "Jia",
        "zweig": "Chen",
        "tier": "Drache",
        "element": "Holz",
    }
    assert body["pillars"]["hour"] == {
        "stamm": "Xin",
        "zweig": "Wei",
        "tier": "Ziege",
        "element": "Metall",
    }
    assert body["dates"]["birth_local"].startswith("2024-02-10T14:30:00")


def test_western_endpoint_success():
    payload = {
        "date": "2024-02-10T14:30:00",
        "tz": "Europe/Berlin",
        "lon": 13.405,
        "lat": 52.52,
    }
    resp = client.post("/calculate/western", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "jd_ut" in body
    assert body["house_system"] in {"P", "O", "W"}
    assert "Sun" in body["bodies"]
    assert "1" in body["houses"]
    assert "Ascendant" in body["angles"]


def test_legacy_api_endpoint_sun_sign():
    resp = client.get(
        "/api",
        params={
            "datum": "2024-02-10",
            "zeit": "14:30:00",
            "tz": "Europe/Berlin",
            "lat": 52.52,
            "lon": 13.405,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    # Echoed input should match the request parameters
    assert body["input"]["datum"] == "2024-02-10"
    assert body["input"]["zeit"] == "14:30:00"
    assert body["input"]["tz"] == "Europe/Berlin"
    assert body["input"]["lat"] == 52.52
    assert body["input"]["lon"] == 13.405

    assert body["sonne"] in {
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
    }
