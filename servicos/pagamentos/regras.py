from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from comum.eventos import EventoDominio, novo_evento
from servicos.pagamentos.modelos import EventoOutbox, EventoProcessado, Pagamento


def deve_recusar(token: str) -> bool:
    token_normalizado = token.strip().lower()
    return token_normalizado == "recusar"


def processar_pagamento(sessao: Session, evento: EventoDominio) -> str:
    if sessao.get(EventoProcessado, evento.id_evento):
        return "duplicado"
    existente = sessao.get(Pagamento, evento.correlacao_id)
    if existente:
        sessao.add(EventoProcessado(id_evento=evento.id_evento))
        sessao.commit()
        return "duplicado"

    token = str(evento.dados["token_pagamento"])
    recusado = deve_recusar(token)
    estado = "RECUSADO" if recusado else "APROVADO"
    referencia = None if recusado else str(uuid4())
    motivo = "Pagamento não autorizado pela operadora" if recusado else None
    pagamento = Pagamento(
        pedido_id=evento.correlacao_id,
        estado=estado,
        valor=Decimal(str(evento.dados["total"])),
        referencia=referencia,
        final_token=token[-4:],
        motivo=motivo,
    )
    tipo_evento = "pagamento.recusado" if recusado else "pagamento.aprovado"
    resposta = novo_evento(
        tipo_evento,
        evento.correlacao_id,
        {
            "pedido_id": evento.correlacao_id,
            "referencia": referencia,
            "motivo": motivo,
            "valor": evento.dados["total"],
        },
    )
    sessao.add(pagamento)
    sessao.add(EventoProcessado(id_evento=evento.id_evento))
    sessao.add(EventoOutbox(conteudo=resposta.model_dump(mode="json")))
    sessao.commit()
    return estado.lower()
