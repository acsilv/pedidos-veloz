from datetime import UTC, datetime, timedelta

from comum.eventos import novo_evento
from comum.mensageria import marcar_evento_publicado, reservar_evento_outbox
from servicos.pedidos.modelos import Base, EventoOutbox


def test_outbox_bloqueia_repeticao_e_marca_publicacao(criar_sessoes):
    fabrica = criar_sessoes(Base)
    evento = novo_evento("pedido.criado", "pedido-1", {"pedido_id": "pedido-1"})
    with fabrica() as sessao:
        sessao.add(EventoOutbox(conteudo=evento.model_dump(mode="json")))
        sessao.commit()

    reservado = reservar_evento_outbox(fabrica, EventoOutbox)
    assert reservado is not None
    assert reservar_evento_outbox(fabrica, EventoOutbox) is None

    marcar_evento_publicado(fabrica, EventoOutbox, reservado["id"])
    with fabrica() as sessao:
        registro = sessao.get(EventoOutbox, reservado["id"])
        assert registro.publicado_em is not None


def test_outbox_tenta_novamente_depois_do_bloqueio(criar_sessoes):
    fabrica = criar_sessoes(Base)
    evento = novo_evento("pedido.criado", "pedido-2", {"pedido_id": "pedido-2"})
    with fabrica() as sessao:
        registro = EventoOutbox(conteudo=evento.model_dump(mode="json"))
        registro.bloqueado_ate = datetime.now(UTC) - timedelta(seconds=1)
        sessao.add(registro)
        sessao.commit()

    assert reservar_evento_outbox(fabrica, EventoOutbox) is not None
