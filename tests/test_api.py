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
    assert body["pillars"]["year"] == "JiaChen"
    assert body["pillars"]["month"] == "BingYin"
    assert body["pillars"]["day"] == "JiaChen"
    assert body["pillars"]["hour"] == "XinWei"
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
