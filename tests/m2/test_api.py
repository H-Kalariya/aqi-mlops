"""Owner: Member 2 — Tests for FastAPI serving, metrics, validation, and version headers."""

import pytest
from fastapi.testclient import TestClient
from api.app import app, model_loader


class StubBooster:
    """Mock LightGBM booster for API testing."""

    def predict(self, X):
        import numpy as np
        return np.full(len(X), 125.0)


@pytest.fixture(autouse=True)
def setup_stub_model(monkeypatch):
    """Ensure a loaded model exists in model_loader for tests."""
    monkeypatch.setattr(model_loader, "load", lambda: None)
    model_loader.model = StubBooster()
    model_loader.model_version = "v1-test"
    model_loader.model_alias = "champion"
    model_loader.is_loaded = True



def test_health_endpoint():
    """Verify /health returns 200, model status, and version headers."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "X-App-Version" in resp.headers
    assert "X-Model-Version" in resp.headers


def test_metrics_endpoint():
    """Verify /metrics exposes the required Prometheus metric names."""
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "aqi_http_requests_total" in text
    assert "aqi_request_latency_seconds" in text
    assert "aqi_errors_total" in text
    assert "aqi_prediction_value" in text


def test_predict_endpoint_success():
    """Verify /predict returns 24-hour forecast with proper schema."""
    client = TestClient(app)
    payload = {
        "city": "ahmedabad",
        "readings": {
            "pm25": 85.2,
            "pm10": 140.0,
            "no2": 30.1,
            "so2": 9.0,
            "co": 1.1,
            "o3": 40.0,
            "temperature": 29.0,
            "humidity": 55.0,
            "wind_speed": 3.2,
        },
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "ahmedabad"
    assert data["model_alias"] == "champion"
    assert len(data["forecast"]) == 24
    assert data["forecast"][0]["horizon_h"] == 1
    assert data["forecast"][23]["horizon_h"] == 24


def test_predict_bad_input_validation():
    """Verify invalid input (missing required pollutant) returns 422 Unprocessable Entity."""
    client = TestClient(app)
    bad_payload = {
        "city": "unknown_city",
        "readings": {
            "pm25": -50.0  # Invalid negative reading
        },
    }
    resp = client.post("/predict", json=bad_payload)
    assert resp.status_code == 422
    assert "X-App-Version" in resp.headers
