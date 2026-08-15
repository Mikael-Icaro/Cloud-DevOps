from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_pedido_inexistente():
    resp = client.get("/pedidos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
