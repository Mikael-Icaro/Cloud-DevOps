from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_consultar_item_seed():
    resp = client.get("/itens/SKU-001")
    assert resp.status_code == 200
    assert resp.json()["sku"] == "SKU-001"


def test_consultar_item_inexistente():
    assert client.get("/itens/SKU-INEXISTENTE").status_code == 404


def test_reservar_estoque_insuficiente():
    resp = client.post("/itens/SKU-001/reservar", json={"quantidade": 999999})
    assert resp.status_code == 409


def test_reservar_e_repor():
    disponivel = client.get("/itens/SKU-002").json()["quantidade"]

    client.post("/itens/SKU-002/reservar", json={"quantidade": 1})
    assert client.get("/itens/SKU-002").json()["quantidade"] == disponivel - 1

    client.post("/itens/SKU-002/repor", json={"quantidade": 1})
    assert client.get("/itens/SKU-002").json()["quantidade"] == disponivel
