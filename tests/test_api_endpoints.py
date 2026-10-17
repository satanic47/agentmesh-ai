import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_status():
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "node_count" in data
    assert "edge_count" in data
    assert "engine_mode" in data

def test_graph_elements():
    res = client.get("/api/graph/elements")
    assert res.status_code == 200
    elements = res.json()
    assert isinstance(elements, list)
    assert len(elements) > 0

def test_cypher_query_endpoint():
    res = client.post("/api/graph/query", json={
        "query": "MATCH (t:Task) RETURN t.title AS title LIMIT 3"
    })
    assert res.status_code == 200
    data = res.json()
    assert "latency_ms" in data
    assert "records" in data

def test_swarm_step_api():
    res = client.post("/api/swarm/step")
    assert res.status_code == 200
    data = res.json()
    assert "executed" in data
