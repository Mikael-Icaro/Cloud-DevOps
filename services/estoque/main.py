import os
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://loja:loja@postgres:5432/loja_veloz")

app = FastAPI(title="Estoque")
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
            CREATE TABLE IF NOT EXISTS estoque_itens (
                sku VARCHAR(50) PRIMARY KEY,
                quantidade INTEGER NOT NULL DEFAULT 0
            )
        """))
        conn.execute(text("""
            INSERT INTO estoque_itens (sku, quantidade)
            VALUES ('SKU-001', 50), ('SKU-002', 30)
            ON CONFLICT (sku) DO NOTHING
        """))


class MovimentoEstoque(BaseModel):
    quantidade: int


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


@app.get("/itens/{sku}")
def consultar_item(sku: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT sku, quantidade FROM estoque_itens WHERE sku = :sku"),
            {"sku": sku},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="item nao encontrado")
    return {"sku": row.sku, "quantidade": row.quantidade}


@app.post("/itens/{sku}/reservar")
def reservar_item(sku: str, movimento: MovimentoEstoque):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT quantidade FROM estoque_itens WHERE sku = :sku FOR UPDATE"),
            {"sku": sku},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="item nao encontrado")
        if row.quantidade < movimento.quantidade:
            raise HTTPException(status_code=409, detail="estoque insuficiente")
        conn.execute(
            text("UPDATE estoque_itens SET quantidade = quantidade - :qtd WHERE sku = :sku"),
            {"qtd": movimento.quantidade, "sku": sku},
        )
    return {"sku": sku, "reservado": movimento.quantidade}


@app.post("/itens/{sku}/repor")
def repor_item(sku: str, movimento: MovimentoEstoque):
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE estoque_itens SET quantidade = quantidade + :qtd WHERE sku = :sku"),
            {"qtd": movimento.quantidade, "sku": sku},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="item nao encontrado")
    return {"sku": sku, "reposto": movimento.quantidade}
