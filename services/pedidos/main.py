import json
import os
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://loja:loja@postgres:5432/loja_veloz")
ESTOQUE_URL = os.getenv("ESTOQUE_URL", "http://estoque:8000")
PAGAMENTOS_URL = os.getenv("PAGAMENTOS_URL", "http://pagamentos:8000")

app = FastAPI(title="Pedidos")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _connect_com_retry(tentativas=10, espera=2):
    for i in range(tentativas):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            if i == tentativas - 1:
                raise
            time.sleep(espera)


@app.on_event("startup")
def preparar_banco():
    _connect_com_retry()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id UUID PRIMARY KEY,
                cliente VARCHAR(120) NOT NULL,
                sku VARCHAR(50) NOT NULL,
                quantidade INTEGER NOT NULL,
                valor NUMERIC(10,2) NOT NULL,
                status VARCHAR(30) NOT NULL,
                criado_em TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        # Log de eventos local. Um broker de verdade (RabbitMQ/Kafka) fica
        # como proximo passo quando existir mais de um consumidor do evento
        # PedidoCriado -- ver justificativa no relatorio tecnico.
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS eventos (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                pedido_id UUID NOT NULL,
                payload JSONB,
                criado_em TIMESTAMP NOT NULL DEFAULT now()
            )
        """))


class NovoPedido(BaseModel):
    cliente: str
    sku: str
    quantidade: int
    valor: float


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(status_code=503, detail="banco indisponivel")
    return {"status": "ready"}


def _registrar_evento(conn, tipo: str, pedido_id: str, payload: dict):
    conn.execute(
        text("INSERT INTO eventos (tipo, pedido_id, payload) VALUES (:tipo, :pedido_id, CAST(:payload AS JSONB))"),
        {"tipo": tipo, "pedido_id": pedido_id, "payload": json.dumps(payload)},
    )


@app.post("/pedidos")
def criar_pedido(pedido: NovoPedido):
    pedido_id = str(uuid.uuid4())

    with httpx.Client(timeout=5.0) as client:
        resp_estoque = client.post(
            f"{ESTOQUE_URL}/itens/{pedido.sku}/reservar",
            json={"quantidade": pedido.quantidade},
        )
        if resp_estoque.status_code == 409:
            raise HTTPException(status_code=409, detail="estoque insuficiente")
        if resp_estoque.status_code == 404:
            raise HTTPException(status_code=404, detail="sku nao encontrado")
        resp_estoque.raise_for_status()

        resp_pagamento = client.post(
            f"{PAGAMENTOS_URL}/pagamentos",
            json={"pedido_id": pedido_id, "valor": pedido.valor},
        )
        resp_pagamento.raise_for_status()
        pagamento = resp_pagamento.json()

    if pagamento["status"] != "aprovado":
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{ESTOQUE_URL}/itens/{pedido.sku}/repor", json={"quantidade": pedido.quantidade})
        status_final = "pagamento_recusado"
    else:
        status_final = "confirmado"

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO pedidos (id, cliente, sku, quantidade, valor, status)
                VALUES (:id, :cliente, :sku, :quantidade, :valor, :status)
            """),
            {
                "id": pedido_id,
                "cliente": pedido.cliente,
                "sku": pedido.sku,
                "quantidade": pedido.quantidade,
                "valor": pedido.valor,
                "status": status_final,
            },
        )
        _registrar_evento(conn, "PedidoCriado", pedido_id, {"status": status_final})

    if status_final != "confirmado":
        raise HTTPException(status_code=402, detail="pagamento recusado")

    return {"id": pedido_id, "status": status_final}


@app.get("/pedidos/{pedido_id}")
def consultar_pedido(pedido_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, cliente, sku, quantidade, valor, status, criado_em FROM pedidos WHERE id = :id"),
            {"id": pedido_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="pedido nao encontrado")
    return {
        "id": str(row.id),
        "cliente": row.cliente,
        "sku": row.sku,
        "quantidade": row.quantidade,
        "valor": float(row.valor),
        "status": row.status,
        "criado_em": row.criado_em.isoformat(),
    }
