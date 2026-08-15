import pytest
from pydantic import ValidationError

from servicos.gateway.esquemas import PedidoEntrada


def test_rejeita_sku_duplicado() -> None:
    with pytest.raises(ValidationError, match="duas vezes"):
        PedidoEntrada.model_validate(
            {
                "cliente_id": "cliente-1",
                "token_pagamento": "tok_teste",
                "itens": [
                    {"sku": "sku-camiseta", "quantidade": 1, "preco_unitario": "79.90"},
                    {"sku": "SKU-CAMISETA", "quantidade": 1, "preco_unitario": "79.90"},
                ],
            }
        )


def test_rejeita_quantidade_zero() -> None:
    with pytest.raises(ValidationError):
        PedidoEntrada.model_validate(
            {
                "cliente_id": "cliente-1",
                "token_pagamento": "tok_teste",
                "itens": [
                    {"sku": "SKU-CAMISETA", "quantidade": 0, "preco_unitario": "79.90"}
                ],
            }
        )
