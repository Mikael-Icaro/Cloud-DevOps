from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_readyz():
    assert client.get("/readyz").status_code == 200


def test_servico_desconhecido():
    resp = client.get("/api/inexistente/algo")
    assert resp.status_code == 404
