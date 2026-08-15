from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_processar_pagamento():
    resp = client.post("/pagamentos", json={"pedido_id": "abc-123", "valor": 42.5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("aprovado", "recusado")
    assert body["pedido_id"] == "abc-123"
    assert "transacao_id" in body
