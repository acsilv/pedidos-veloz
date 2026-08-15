from decimal import Decimal

from comum.eventos import EventoDominio
from servicos.estoque.modelos import Base as BaseEstoque
from servicos.estoque.modelos import EventoOutbox as OutboxEstoque
from servicos.estoque.regras import carregar_estoque_inicial, consultar_produto, processar_evento
from servicos.pagamentos.modelos import Base as BasePagamentos
from servicos.pagamentos.modelos import EventoOutbox as OutboxPagamentos
from servicos.pagamentos.regras import processar_pagamento
from servicos.pedidos.esquemas import ItemNovoPedido, NovoPedido
from servicos.pedidos.modelos import Base as BasePedidos
from servicos.pedidos.modelos import EventoOutbox as OutboxPedidos
from servicos.pedidos.regras import criar_pedido, obter_pedido, processar_resultado


def ler_evento_outbox(sessao, modelo) -> EventoDominio:
    registro = sessao.query(modelo).order_by(modelo.criado_em.desc()).first()
    assert registro is not None
    return EventoDominio.model_validate(registro.conteudo)


def montar_pedido(
    token: str = "tok_aprovado",
    quantidade: int = 2,
    sku: str = "SKU-CAMISETA",
) -> NovoPedido:
    return NovoPedido(
        cliente_id="cliente-teste",
        token_pagamento=token,
        itens=[
            ItemNovoPedido(
                sku=sku,
                quantidade=quantidade,
                preco_unitario=Decimal("79.90"),
            )
        ],
    )


def preparar_bancos(criar_sessoes):
    pedidos = criar_sessoes(BasePedidos)
    estoque = criar_sessoes(BaseEstoque)
    pagamentos = criar_sessoes(BasePagamentos)
    with estoque() as sessao:
        carregar_estoque_inicial(sessao)
    return pedidos, estoque, pagamentos


def test_pedido_confirmado_de_ponta_a_ponta(criar_sessoes):
    pedidos, estoque, pagamentos = preparar_bancos(criar_sessoes)

    with pedidos() as sessao:
        pedido = criar_pedido(sessao, montar_pedido())
        pedido_id = pedido.id
        pedido_criado = ler_evento_outbox(sessao, OutboxPedidos)

    with estoque() as sessao:
        assert processar_evento(sessao, pedido_criado) == "reservado"
        estoque_reservado = ler_evento_outbox(sessao, OutboxEstoque)

    with pedidos() as sessao:
        assert processar_resultado(sessao, estoque_reservado)
        assert obter_pedido(sessao, pedido_id).estado == "AGUARDANDO_PAGAMENTO"

    with pagamentos() as sessao:
        assert processar_pagamento(sessao, estoque_reservado) == "aprovado"
        pagamento_aprovado = ler_evento_outbox(sessao, OutboxPagamentos)

    with pedidos() as sessao:
        processar_resultado(sessao, pagamento_aprovado)
        assert obter_pedido(sessao, pedido_id).estado == "CONFIRMADO"

    with estoque() as sessao:
        assert processar_evento(sessao, pagamento_aprovado) == "confirmada"
        produto = consultar_produto(sessao, "SKU-CAMISETA")
        assert produto.quantidade_disponivel == 98
        assert produto.quantidade_reservada == 0


def test_estoque_insuficiente_cancela_sem_cobrar(criar_sessoes):
    pedidos, estoque, _ = preparar_bancos(criar_sessoes)
    with pedidos() as sessao:
        pedido = criar_pedido(sessao, montar_pedido(quantidade=21, sku="SKU-MOCHILA"))
        pedido_id = pedido.id
        pedido_criado = ler_evento_outbox(sessao, OutboxPedidos)

    with estoque() as sessao:
        assert processar_evento(sessao, pedido_criado) == "insuficiente"
        evento = ler_evento_outbox(sessao, OutboxEstoque)

    with pedidos() as sessao:
        processar_resultado(sessao, evento)
        pedido = obter_pedido(sessao, pedido_id)
        assert pedido.estado == "CANCELADO"
        assert "SKU-MOCHILA" in pedido.motivo_cancelamento


def test_pagamento_recusado_devolve_estoque(criar_sessoes):
    pedidos, estoque, pagamentos = preparar_bancos(criar_sessoes)
    with pedidos() as sessao:
        pedido = criar_pedido(sessao, montar_pedido(token="falha_teste"))
        pedido_id = pedido.id
        pedido_criado = ler_evento_outbox(sessao, OutboxPedidos)
    with estoque() as sessao:
        processar_evento(sessao, pedido_criado)
        estoque_reservado = ler_evento_outbox(sessao, OutboxEstoque)
    with pedidos() as sessao:
        processar_resultado(sessao, estoque_reservado)
    with pagamentos() as sessao:
        assert processar_pagamento(sessao, estoque_reservado) == "recusado"
        pagamento_recusado = ler_evento_outbox(sessao, OutboxPagamentos)
    with pedidos() as sessao:
        processar_resultado(sessao, pagamento_recusado)
        pedido_cancelado = obter_pedido(sessao, pedido_id)
        assert pedido_cancelado.estado == "CANCELADO"
        assert pedido_cancelado.motivo_cancelamento == "Pagamento não autorizado pela operadora"
    with estoque() as sessao:
        processar_evento(sessao, pagamento_recusado)
        produto = consultar_produto(sessao, "SKU-CAMISETA")
        assert produto.quantidade_disponivel == 100
        assert produto.quantidade_reservada == 0


def test_evento_duplicado_nao_movimenta_estoque_duas_vezes(criar_sessoes):
    pedidos, estoque, _ = preparar_bancos(criar_sessoes)
    with pedidos() as sessao:
        criar_pedido(sessao, montar_pedido())
        evento = ler_evento_outbox(sessao, OutboxPedidos)
    with estoque() as sessao:
        assert processar_evento(sessao, evento) == "reservado"
        assert processar_evento(sessao, evento) == "duplicado"
        assert consultar_produto(sessao, "SKU-CAMISETA").quantidade_disponivel == 98
