import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client and run the FastAPI lifespan events."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Verify the health endpoint returns 200 OK."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "Hardware RAG API is up and running!"
    }


def test_query_happy_path(client):
    """Verify a valid question returns a 200 OK with the correct grounded answer and sources."""
    payload = {
        "question": "How much flash memory does the Arduino Uno have?"
    }

    # This test uses the real ChromaDB retrieval and Qwen3 LLM.
    # It may take a few seconds because it performs actual generation.
    response = client.post("/query", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)

    assert "32 kB" in data["answer"]
    assert "arduino_uno.pdf" in data["sources"]


def test_query_invalid_input(client):
    """Verify that sending an empty string triggers a 422 Validation Error."""
    payload = {
        "question": ""
    }

    response = client.post("/query", json=payload)

    assert response.status_code == 422