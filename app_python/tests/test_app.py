import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        yield client


def test_index_structure(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # Required top-level keys
    for key in ("service", "system", "runtime", "request", "endpoints"):
        assert key in data


def test_index_service_fields(client):
    resp = client.get("/")
    data = resp.get_json()
    svc = data["service"]
    assert svc["name"] == "devops-info-service"
    assert "version" in svc
    assert "framework" in svc


def test_index_request_fields_with_forwarded_for(client):
    resp = client.get("/", headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.1"})
    data = resp.get_json()
    req = data["request"]
    assert req["client_ip"] == "203.0.113.5"
    assert req["method"] == "GET"
    assert req["path"] == "/"


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "healthy"
    assert "uptime_seconds" in data


def test_404_returns_json(client):
    resp = client.get("/no-such-path")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data.get("error") == "Not Found"
