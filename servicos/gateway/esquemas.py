from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ItemPedidoEntrada(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    quantidade: int = Field(ge=1, le=100)
    preco_unitario: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("sku")
    @classmethod
    def normalizar_sku(cls, valor: str) -> str:
        return valor.strip().upper()


class PedidoEntrada(BaseModel):
    cliente_id: str = Field(min_length=2, max_length=80)
    token_pagamento: str = Field(min_length=4, max_length=120)
    itens: list[ItemPedidoEntrada] = Field(min_length=1, max_length=20)

    @field_validator("itens")
    @classmethod
    def impedir_skus_repetidos(cls, itens: list[ItemPedidoEntrada]) -> list[ItemPedidoEntrada]:
        if len({item.sku for item in itens}) != len(itens):
            raise ValueError("um SKU não pode aparecer duas vezes no mesmo pedido")
        return itens
