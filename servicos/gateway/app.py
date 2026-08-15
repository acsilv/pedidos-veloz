import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status

from comum.observabilidade import configurar_logs, preparar_observabilidade
from servicos.gateway.configuracao import obter_configuracao
from servicos.gateway.esquemas import PedidoEntrada

configuracao = obter_configuracao()
configurar_logs(configuracao.nivel_log)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    app.state.cliente = httpx.AsyncClient(timeout=configuracao.tempo_limite_segundos)
    yield
    await app.state.cliente.aclose()


app = FastAPI(
    title="API Gateway - Pedidos Veloz",
    description="Entrada única para criação e consulta de pedidos da Loja Veloz.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)
preparar_observabilidade(app, configuracao.nome_servico, configuracao.otel_exporter_otlp_endpoint)


def traduzir_resposta(resposta: httpx.Response) -> Response:
    return Response(
        content=resposta.content,
        status_code=resposta.status_code,
        media_type=resposta.headers.get("content-type", "application/json"),
    )


async def chamar_servico(
    request: Request,
    metodo: str,
    url: str,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    cliente: httpx.AsyncClient = request.app.state.cliente
    try:
        return await cliente.request(metodo, url, json=json)
    except httpx.TimeoutException as erro:
        logger.warning("Tempo limite excedido ao chamar %s", url)
        raise HTTPException(status_code=504, detail="Serviço demorou para responder") from erro
    except httpx.RequestError as erro:
        logger.warning("Serviço indisponível em %s", url)
        raise HTTPException(
            status_code=503, detail="Serviço temporariamente indisponível"
        ) from erro


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"estado": "vivo", "servico": configuracao.nome_servico}


@app.get("/pronto")
async def pronto(request: Request) -> dict[str, str]:
    cliente: httpx.AsyncClient = request.app.state.cliente
    resultados = await asyncio.gather(
        cliente.get(f"{configuracao.url_pedidos}/saude"),
        cliente.get(f"{configuracao.url_estoque}/saude"),
        return_exceptions=True,
    )
    if any(isinstance(item, Exception) or item.status_code != 200 for item in resultados):
        raise HTTPException(status_code=503, detail="Serviços internos indisponíveis")
    return {"estado": "pronto"}


@app.post("/api/v1/pedidos", status_code=status.HTTP_202_ACCEPTED)
async def criar_pedido(request: Request, entrada: PedidoEntrada) -> Response:
    resposta = await chamar_servico(
        request,
        "POST",
        f"{configuracao.url_pedidos}/pedidos",
        entrada.model_dump(mode="json"),
    )
    return traduzir_resposta(resposta)


@app.get("/api/v1/pedidos/{pedido_id}")
async def consultar_pedido(request: Request, pedido_id: str) -> Response:
    resposta = await chamar_servico(
        request,
        "GET",
        f"{configuracao.url_pedidos}/pedidos/{pedido_id}",
    )
    return traduzir_resposta(resposta)


@app.get("/api/v1/estoque/{sku}")
async def consultar_estoque(request: Request, sku: str) -> Response:
    resposta = await chamar_servico(
        request,
        "GET",
        f"{configuracao.url_estoque}/estoque/{sku}",
    )
    return traduzir_resposta(resposta)
