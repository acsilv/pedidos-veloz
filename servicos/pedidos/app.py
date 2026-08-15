import asyncio
import logging
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
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
from servicos.pedidos.configuracao import obter_configuracao
from servicos.pedidos.esquemas import NovoPedido, PedidoAceito, PedidoResposta
from servicos.pedidos.modelos import Base, EventoOutbox, Pedido
from servicos.pedidos.regras import criar_pedido, obter_pedido, processar_resultado

configuracao = obter_configuracao()
configurar_logs(configuracao.nivel_log)
logger = logging.getLogger(__name__)
fabrica_sessoes = criar_fabrica_sessoes(configuracao.banco_url)
barramento = BarramentoEventos(configuracao.rabbitmq_url, configuracao.exchange_eventos)
PEDIDOS_CRIADOS = Counter("pedidos_criados_total", "Pedidos aceitos pelo serviço")
EVENTOS_PROCESSADOS = Counter(
    "pedidos_eventos_processados_total", "Resultados processados", ["tipo"]
)


def obter_sessao() -> Generator[Session, None, None]:
    yield from criar_dependencia_sessao(fabrica_sessoes)


async def receber_resultado(evento: EventoDominio) -> None:
    def executar() -> bool:
        with fabrica_sessoes() as sessao:
            return processar_resultado(sessao, evento)

    if await asyncio.to_thread(executar):
        EVENTOS_PROCESSADOS.labels(evento.tipo).inc()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(fabrica_sessoes.kw["bind"])
    consumidor = asyncio.create_task(
        conectar_com_retentativa(
            barramento,
            configuracao.fila_resultados,
            ["estoque.reservado", "estoque.insuficiente", "pagamento.*"],
            receber_resultado,
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
    title="Serviço de Pedidos - Loja Veloz",
    version="1.0.0",
    lifespan=ciclo_de_vida,
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


@app.post(
    "/pedidos",
    response_model=PedidoAceito,
    status_code=status.HTTP_202_ACCEPTED,
)
def novo_pedido(
    entrada: NovoPedido,
    sessao: Session = Depends(obter_sessao),
) -> PedidoAceito:
    pedido = criar_pedido(sessao, entrada)
    PEDIDOS_CRIADOS.inc()
    logger.info("Pedido %s recebido", pedido.id)
    return PedidoAceito(
        id=pedido.id,
        estado=pedido.estado,
        mensagem="Pedido recebido e enviado para reserva de estoque",
    )


@app.get("/pedidos/{pedido_id}", response_model=PedidoResposta)
def consultar_pedido(
    pedido_id: str,
    sessao: Session = Depends(obter_sessao),
) -> Pedido:
    pedido = obter_pedido(sessao, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido
