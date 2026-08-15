import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_pedido_inexistente(client):
    resp = client.get("/pedidos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
