import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="API Gateway")

ROTAS = {
    "pedidos": os.getenv("PEDIDOS_URL", "http://pedidos:8000"),
    "estoque": os.getenv("ESTOQUE_URL", "http://estoque:8000"),
    "pagamentos": os.getenv("PAGAMENTOS_URL", "http://pagamentos:8000"),
}

client = httpx.AsyncClient(timeout=10.0)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.api_route("/api/{servico}/{caminho:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def encaminhar(servico: str, caminho: str, request: Request):
    base_url = ROTAS.get(servico)
    if not base_url:
        return JSONResponse(status_code=404, content={"detail": f"servico '{servico}' desconhecido"})

    corpo = await request.body()
    resposta = await client.request(
        request.method,
        f"{base_url}/{caminho}",
        content=corpo,
        params=request.query_params,
        headers={"content-type": request.headers.get("content-type", "application/json")},
    )
    return Response(content=resposta.content, status_code=resposta.status_code, media_type=resposta.headers.get("content-type"))
