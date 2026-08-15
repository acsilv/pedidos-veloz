from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from comum.eventos import EventoDominio, novo_evento
from servicos.pedidos.esquemas import NovoPedido
from servicos.pedidos.modelos import (
    EventoOutbox,
    EventoProcessado,
    HistoricoPedido,
    ItemPedido,
    Pedido,
)


def registrar_historico(pedido: Pedido, estado: str, descricao: str) -> None:
    pedido.estado = estado
    pedido.historico.append(HistoricoPedido(estado=estado, descricao=descricao))


def criar_pedido(sessao: Session, entrada: NovoPedido) -> Pedido:
    pedido_id = str(uuid4())
    total = sum(
        (item.preco_unitario * item.quantidade for item in entrada.itens),
        start=Decimal("0.00"),
    )
    pedido = Pedido(
        id=pedido_id,
        cliente_id=entrada.cliente_id,
        estado="RECEBIDO",
        token_pagamento=entrada.token_pagamento,
        total=total,
        itens=[
            ItemPedido(
                sku=item.sku,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
            )
            for item in entrada.itens
        ],
        historico=[],
    )
    registrar_historico(pedido, "RECEBIDO", "Pedido recebido e validado")
    registrar_historico(
        pedido,
        "AGUARDANDO_ESTOQUE",
        "Solicitação de reserva enviada ao serviço de estoque",
    )
    evento = novo_evento(
        "pedido.criado",
        pedido_id,
        {
            "pedido_id": pedido_id,
            "cliente_id": entrada.cliente_id,
            "token_pagamento": entrada.token_pagamento,
            "total": str(total),
            "itens": [item.model_dump(mode="json") for item in entrada.itens],
        },
    )
    sessao.add(pedido)
    sessao.add(EventoOutbox(conteudo=evento.model_dump(mode="json")))
    sessao.commit()
    sessao.refresh(pedido)
    return pedido


def obter_pedido(sessao: Session, pedido_id: str) -> Pedido | None:
    return sessao.scalar(select(Pedido).where(Pedido.id == pedido_id))


def processar_resultado(sessao: Session, evento: EventoDominio) -> bool:
    if sessao.get(EventoProcessado, evento.id_evento):
        return False
    pedido = sessao.get(Pedido, evento.correlacao_id)
    if not pedido:
        raise ValueError(f"Pedido {evento.correlacao_id} não foi encontrado")

    if evento.tipo == "estoque.reservado" and pedido.estado == "AGUARDANDO_ESTOQUE":
        registrar_historico(
            pedido,
            "AGUARDANDO_PAGAMENTO",
            "Itens reservados; pagamento enviado para processamento",
        )
    elif evento.tipo == "estoque.insuficiente" and pedido.estado == "AGUARDANDO_ESTOQUE":
        pedido.motivo_cancelamento = evento.dados.get("motivo", "Estoque insuficiente")
        registrar_historico(pedido, "CANCELADO", pedido.motivo_cancelamento)
    elif evento.tipo == "pagamento.aprovado" and pedido.estado == "AGUARDANDO_PAGAMENTO":
        registrar_historico(pedido, "CONFIRMADO", "Pagamento aprovado; pedido confirmado")
    elif evento.tipo == "pagamento.recusado" and pedido.estado == "AGUARDANDO_PAGAMENTO":
        pedido.motivo_cancelamento = evento.dados.get("motivo", "Pagamento recusado")
        registrar_historico(pedido, "CANCELADO", pedido.motivo_cancelamento)

    sessao.add(EventoProcessado(id_evento=evento.id_evento))
    sessao.commit()
    return True
