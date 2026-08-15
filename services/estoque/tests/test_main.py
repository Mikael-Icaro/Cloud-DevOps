import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_consultar_item_seed(client):
    resp = client.get("/itens/SKU-001")
    assert resp.status_code == 200
    assert resp.json()["sku"] == "SKU-001"


def test_consultar_item_inexistente(client):
    assert client.get("/itens/SKU-INEXISTENTE").status_code == 404


def test_reservar_estoque_insuficiente(client):
    resp = client.post("/itens/SKU-001/reservar", json={"quantidade": 999999})
    assert resp.status_code == 409


def test_reservar_e_repor(client):
    disponivel = client.get("/itens/SKU-002").json()["quantidade"]

    client.post("/itens/SKU-002/reservar", json={"quantidade": 1})
    assert client.get("/itens/SKU-002").json()["quantidade"] == disponivel - 1

    client.post("/itens/SKU-002/repor", json={"quantidade": 1})
    assert client.get("/itens/SKU-002").json()["quantidade"] == disponivel
