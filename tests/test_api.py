import pytest
from fastapi.testclient import TestClient
from src.main import create_application

@pytest.fixture
def client():
    app = create_application()
    return TestClient(app)

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sentinel Server API" in response.json()["message"]

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_machines_empty(client):
    response = client.get("/machines")
    assert response.status_code == 200
    assert response.json() == {"machines": []}

def test_machine_not_found(client):
    response = client.get("/machine/123")
    assert response.status_code == 404
    assert "Machine not found" in response.json()["detail"]

def test_query_machine_events_default(client):
    response = client.get("/machine-events")
    assert response.status_code == 200
    assert "events" in response.json()
    assert isinstance(response.json()["events"], list)

def test_query_machine_events_bad_day(client):
    response = client.get("/machine-events?day=2024-13-01")
    assert response.status_code == 400
