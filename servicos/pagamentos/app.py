import asyncio
import logging
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from prometheus_client import Counter
from sqlalchemy.orm import Session

from comum.banco import banco_esta_pronto, criar_dependencia_sessao, criar_fabrica_sessoes
from comum.eventos import EventoDominio
from comum.mensageria import (
    BarramentoEventos,
    conectar_com_retentativa,
    executar_publicador_outbox,
)
from comum.observabilidade import configurar_logs, preparar_observabilidade
from servicos.pagamentos.configuracao import obter_configuracao
from servicos.pagamentos.esquemas import PagamentoResposta
from servicos.pagamentos.modelos import Base, EventoOutbox, Pagamento
from servicos.pagamentos.regras import processar_pagamento

configuracao = obter_configuracao()
configurar_logs(configuracao.nivel_log)
logger = logging.getLogger(__name__)
fabrica_sessoes = criar_fabrica_sessoes(configuracao.banco_url)
barramento = BarramentoEventos(configuracao.rabbitmq_url, configuracao.exchange_eventos)
PAGAMENTOS = Counter(
    "pagamentos_processados_total", "Pagamentos processados", ["resultado"]
)


def obter_sessao() -> Generator[Session, None, None]:
    yield from criar_dependencia_sessao(fabrica_sessoes)


async def receber_evento(evento: EventoDominio) -> None:
    def executar() -> str:
        with fabrica_sessoes() as sessao:
            return processar_pagamento(sessao, evento)

    resultado = await asyncio.to_thread(executar)
    PAGAMENTOS.labels(resultado).inc()
    logger.info("Pagamento do pedido %s: %s", evento.correlacao_id, resultado)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(fabrica_sessoes.kw["bind"])
    consumidor = asyncio.create_task(
        conectar_com_retentativa(
            barramento,
            configuracao.fila_eventos,
            ["estoque.reservado"],
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


app = FastAPI(
    title="Serviço de Pagamentos - Loja Veloz", version="1.0.0", lifespan=ciclo_de_vida
)
preparar_observabilidade(app, configuracao.nome_servico, configuracao.otel_exporter_otlp_endpoint)


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"estado": "vivo", "servico": configuracao.nome_servico}


@app.get("/pronto")
def pronto() -> dict[str, str]:
    if not banco_esta_pronto(fabrica_sessoes) or not barramento.conectado:
        raise HTTPException(status_code=503, detail="Dependências ainda não estão disponíveis")
    return {"estado": "pronto"}


@app.get("/pagamentos/{pedido_id}", response_model=PagamentoResposta)
def consultar_pagamento(
    pedido_id: str,
    sessao: Session = Depends(obter_sessao),
) -> Pagamento:
    pagamento = sessao.get(Pagamento, pedido_id)
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return pagamento
