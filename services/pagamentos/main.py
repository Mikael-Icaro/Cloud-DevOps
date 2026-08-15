import random
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Pagamentos")

# Simula uma integradora externa (ex: Stripe, PagSeguro). Taxa de recusa
# fixa em 10% so pra dar sinal de vida pro fluxo de erro no gateway/pedidos.
TAXA_RECUSA = 0.10


class SolicitacaoPagamento(BaseModel):
    pedido_id: str
    valor: float


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/pagamentos")
def processar_pagamento(solicitacao: SolicitacaoPagamento):
    aprovado = random.random() > TAXA_RECUSA
    return {
        "transacao_id": str(uuid.uuid4()),
        "pedido_id": solicitacao.pedido_id,
        "valor": solicitacao.valor,
        "status": "aprovado" if aprovado else "recusado",
    }
