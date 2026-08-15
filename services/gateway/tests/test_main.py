import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_servico_desconhecido(client):
    resp = client.get("/api/inexistente/algo")
    assert resp.status_code == 404
