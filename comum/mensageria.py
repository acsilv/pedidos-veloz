import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from comum.eventos import EventoDominio

logger = logging.getLogger(__name__)
ProcessadorEvento = Callable[[EventoDominio], Awaitable[None]]


class BarramentoEventos:
    def __init__(self, url: str, exchange: str) -> None:
        self.url = url
        self.nome_exchange = exchange
        self.conexao: aio_pika.RobustConnection | None = None
        self.canal: aio_pika.RobustChannel | None = None
        self.exchange: aio_pika.RobustExchange | None = None

    @property
    def conectado(self) -> bool:
        return bool(self.conexao and not self.conexao.is_closed)

    async def conectar(self) -> None:
        if self.conectado:
            return
        self.conexao = await aio_pika.connect_robust(self.url)
        self.canal = await self.conexao.channel(publisher_confirms=True)
        await self.canal.set_qos(prefetch_count=20)
        self.exchange = await self.canal.declare_exchange(
            self.nome_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

    async def publicar(self, evento: EventoDominio) -> None:
        await self.conectar()
        assert self.exchange is not None
        cabecalhos: dict[str, str] = {}
        propagate.inject(cabecalhos)
        rastreador = trace.get_tracer("pedidos-veloz.mensageria")
        with rastreador.start_as_current_span(
            f"publicar {evento.tipo}", kind=SpanKind.PRODUCER
        ):
            await self.exchange.publish(
                Message(
                    body=evento.para_json().encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    correlation_id=evento.correlacao_id,
                    message_id=evento.id_evento,
                    headers=cabecalhos,
                ),
                routing_key=evento.tipo,
            )

    async def consumir(
        self,
        nome_fila: str,
        chaves: list[str],
        processador: ProcessadorEvento,
    ) -> None:
        await self.conectar()
        assert self.canal is not None and self.exchange is not None
        fila = await self.canal.declare_queue(nome_fila, durable=True)
        for chave in chaves:
            await fila.bind(self.exchange, routing_key=chave)

        async def ao_receber(mensagem: aio_pika.IncomingMessage) -> None:
            contexto = propagate.extract(mensagem.headers or {})
            rastreador = trace.get_tracer("pedidos-veloz.mensageria")
            async with mensagem.process(requeue=True, ignore_processed=True):
                with rastreador.start_as_current_span(
                    f"consumir {mensagem.routing_key}",
                    context=contexto,
                    kind=SpanKind.CONSUMER,
                ):
                    evento = EventoDominio.model_validate_json(mensagem.body)
                    await processador(evento)

        await fila.consume(ao_receber)

    async def fechar(self) -> None:
        if self.conexao and not self.conexao.is_closed:
            await self.conexao.close()


def reservar_evento_outbox(
    fabrica: sessionmaker[Session], modelo: Any
) -> dict[str, Any] | None:
    agora = datetime.now(UTC)
    with fabrica() as sessao:
        registro = sessao.scalar(
            select(modelo)
            .where(
                modelo.publicado_em.is_(None),
                or_(modelo.bloqueado_ate.is_(None), modelo.bloqueado_ate < agora),
            )
            .order_by(modelo.criado_em)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not registro:
            return None
        registro.bloqueado_ate = agora + timedelta(seconds=30)
        registro.tentativas += 1
        sessao.commit()
        return {"id": registro.id, "evento": registro.conteudo}


def marcar_evento_publicado(fabrica: sessionmaker[Session], modelo: Any, registro_id: str) -> None:
    with fabrica() as sessao:
        registro = sessao.get(modelo, registro_id)
        if registro:
            registro.publicado_em = datetime.now(UTC)
            registro.bloqueado_ate = None
            sessao.commit()


async def executar_publicador_outbox(
    fabrica: sessionmaker[Session],
    modelo: Any,
    barramento: BarramentoEventos,
    intervalo: float = 1.0,
) -> None:
    while True:
        try:
            reservado = await asyncio.to_thread(reservar_evento_outbox, fabrica, modelo)
            if not reservado:
                await asyncio.sleep(intervalo)
                continue
            evento = EventoDominio.model_validate(reservado["evento"])
            await barramento.publicar(evento)
            await asyncio.to_thread(
                marcar_evento_publicado, fabrica, modelo, reservado["id"]
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Falha ao publicar evento da outbox; uma nova tentativa será feita")
            await asyncio.sleep(3)


async def conectar_com_retentativa(
    barramento: BarramentoEventos,
    nome_fila: str,
    chaves: list[str],
    processador: ProcessadorEvento,
) -> None:
    while True:
        try:
            await barramento.consumir(nome_fila, chaves, processador)
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("RabbitMQ indisponível; nova tentativa em cinco segundos")
            await asyncio.sleep(5)
