import asyncio
import logging
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from prometheus_client import Counter, Gauge
from sqlalchemy.orm import Session

from comum.banco import banco_esta_pronto, criar_dependencia_sessao, criar_fabrica_sessoes
from comum.eventos import EventoDominio
from comum.mensageria import (
    BarramentoEventos,
    conectar_com_retentativa,
    executar_publicador_outbox,
)
from comum.observabilidade import configurar_logs, preparar_observabilidade
from servicos.estoque.configuracao import obter_configuracao
from servicos.estoque.esquemas import ProdutoResposta
from servicos.estoque.modelos import Base, EventoOutbox, Produto
from servicos.estoque.regras import carregar_estoque_inicial, consultar_produto, processar_evento

configuracao = obter_configuracao()
configurar_logs(configuracao.nivel_log)
logger = logging.getLogger(__name__)
fabrica_sessoes = criar_fabrica_sessoes(configuracao.banco_url)
barramento = BarramentoEventos(configuracao.rabbitmq_url, configuracao.exchange_eventos)
EVENTOS_ESTOQUE = Counter(
    "estoque_eventos_processados_total", "Eventos tratados pelo estoque", ["tipo", "resultado"]
)
ESTOQUE_DISPONIVEL = Gauge(
    "estoque_quantidade_disponivel", "Quantidade disponível por produto", ["sku"]
)


def obter_sessao() -> Generator[Session, None, None]:
    yield from criar_dependencia_sessao(fabrica_sessoes)


async def receber_evento(evento: EventoDominio) -> None:
    def executar() -> str:
        with fabrica_sessoes() as sessao:
            return processar_evento(sessao, evento)

    resultado = await asyncio.to_thread(executar)
    EVENTOS_ESTOQUE.labels(evento.tipo, resultado).inc()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(fabrica_sessoes.kw["bind"])
    with fabrica_sessoes() as sessao:
        carregar_estoque_inicial(sessao)
    consumidor = asyncio.create_task(
        conectar_com_retentativa(
            barramento,
            configuracao.fila_eventos,
            ["pedido.criado", "pagamento.*"],
            receber_evento,
        )
    )
    publicador = asyncio.create_task(
        executar_publicador_outbox(fabrica_sessoes, EventoOutbox, barramento)
    )
    yield
    consumidor.cancel()
    publicador.cancel()
    await barramento.fechar()


app = FastAPI(title="Serviço de Estoque - Loja Veloz", version="1.0.0", lifespan=ciclo_de_vida)
preparar_observabilidade(app, configuracao.nome_servico, configuracao.otel_exporter_otlp_endpoint)


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"estado": "vivo", "servico": configuracao.nome_servico}


@app.get("/pronto")
def pronto() -> dict[str, str]:
    if not banco_esta_pronto(fabrica_sessoes) or not barramento.conectado:
        raise HTTPException(status_code=503, detail="Dependências ainda não estão disponíveis")
    return {"estado": "pronto"}


@app.get("/estoque/{sku}", response_model=ProdutoResposta)
def obter_estoque(sku: str, sessao: Session = Depends(obter_sessao)) -> Produto:
    produto = consultar_produto(sessao, sku)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    ESTOQUE_DISPONIVEL.labels(produto.sku).set(produto.quantidade_disponivel)
    return produto
