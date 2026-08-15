from sqlalchemy import select
from sqlalchemy.orm import Session

from comum.eventos import EventoDominio, novo_evento
from servicos.estoque.modelos import (
    EventoOutbox,
    EventoProcessado,
    Produto,
    Reserva,
)

PRODUTOS_INICIAIS = [
    Produto(sku="SKU-CAMISETA", nome="Camiseta Veloz", quantidade_disponivel=100),
    Produto(sku="SKU-TENIS", nome="Tênis Urbano", quantidade_disponivel=30),
    Produto(sku="SKU-MOCHILA", nome="Mochila Essencial", quantidade_disponivel=20),
]


def carregar_estoque_inicial(sessao: Session) -> None:
    if sessao.scalar(select(Produto.sku).limit(1)):
        return
    for produto in PRODUTOS_INICIAIS:
        sessao.merge(produto)
    sessao.commit()


def consultar_produto(sessao: Session, sku: str) -> Produto | None:
    return sessao.get(Produto, sku.upper())


def _registrar_saida(sessao: Session, evento: EventoDominio) -> None:
    sessao.add(EventoOutbox(conteudo=evento.model_dump(mode="json")))


def reservar_itens(sessao: Session, evento: EventoDominio) -> str:
    if sessao.get(EventoProcessado, evento.id_evento):
        return "duplicado"
    if sessao.get(Reserva, evento.correlacao_id):
        sessao.add(EventoProcessado(id_evento=evento.id_evento))
        sessao.commit()
        return "duplicado"

    itens = evento.dados["itens"]
    produtos: dict[str, Produto] = {}
    faltantes: list[str] = []
    for item in itens:
        produto = sessao.scalar(
            select(Produto).where(Produto.sku == item["sku"]).with_for_update()
        )
        produtos[item["sku"]] = produto
        if not produto or produto.quantidade_disponivel < int(item["quantidade"]):
            faltantes.append(item["sku"])

    if faltantes:
        reserva = Reserva(pedido_id=evento.correlacao_id, estado="RECUSADA", itens=itens)
        resposta = novo_evento(
            "estoque.insuficiente",
            evento.correlacao_id,
            {
                "pedido_id": evento.correlacao_id,
                "motivo": f"Sem quantidade suficiente para: {', '.join(faltantes)}",
                "skus": faltantes,
            },
        )
        resultado = "insuficiente"
    else:
        for item in itens:
            produto = produtos[item["sku"]]
            quantidade = int(item["quantidade"])
            produto.quantidade_disponivel -= quantidade
            produto.quantidade_reservada += quantidade
        reserva = Reserva(pedido_id=evento.correlacao_id, estado="RESERVADA", itens=itens)
        resposta = novo_evento(
            "estoque.reservado",
            evento.correlacao_id,
            {
                "pedido_id": evento.correlacao_id,
                "token_pagamento": evento.dados["token_pagamento"],
                "total": evento.dados["total"],
                "itens": itens,
            },
        )
        resultado = "reservado"

    sessao.add(reserva)
    sessao.add(EventoProcessado(id_evento=evento.id_evento))
    _registrar_saida(sessao, resposta)
    sessao.commit()
    return resultado


def finalizar_reserva(sessao: Session, evento: EventoDominio) -> str:
    if sessao.get(EventoProcessado, evento.id_evento):
        return "duplicado"
    reserva = sessao.get(Reserva, evento.correlacao_id)
    if not reserva or reserva.estado != "RESERVADA":
        sessao.add(EventoProcessado(id_evento=evento.id_evento))
        sessao.commit()
        return "ignorado"

    for item in reserva.itens:
        produto = sessao.scalar(
            select(Produto).where(Produto.sku == item["sku"]).with_for_update()
        )
        if produto:
            quantidade = int(item["quantidade"])
            produto.quantidade_reservada -= quantidade
            if evento.tipo == "pagamento.recusado":
                produto.quantidade_disponivel += quantidade

    reserva.estado = "CONFIRMADA" if evento.tipo == "pagamento.aprovado" else "LIBERADA"
    sessao.add(EventoProcessado(id_evento=evento.id_evento))
    sessao.commit()
    return reserva.estado.lower()


def processar_evento(sessao: Session, evento: EventoDominio) -> str:
    if evento.tipo == "pedido.criado":
        return reservar_itens(sessao, evento)
    if evento.tipo in {"pagamento.aprovado", "pagamento.recusado"}:
        return finalizar_reserva(sessao, evento)
    return "ignorado"
