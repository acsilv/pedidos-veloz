from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemNovoPedido(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    quantidade: int = Field(ge=1, le=100)
    preco_unitario: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("sku")
    @classmethod
    def normalizar_sku(cls, valor: str) -> str:
        return valor.strip().upper()


class NovoPedido(BaseModel):
    cliente_id: str = Field(min_length=2, max_length=80)
    token_pagamento: str = Field(min_length=4, max_length=120)
    itens: list[ItemNovoPedido] = Field(min_length=1, max_length=20)

    @field_validator("itens")
    @classmethod
    def impedir_skus_repetidos(cls, itens: list[ItemNovoPedido]) -> list[ItemNovoPedido]:
        skus = [item.sku for item in itens]
        if len(skus) != len(set(skus)):
            raise ValueError("um SKU não pode aparecer duas vezes no mesmo pedido")
        return itens


class ItemPedidoResposta(BaseModel):
    sku: str
    quantidade: int
    preco_unitario: Decimal

    model_config = ConfigDict(from_attributes=True)


class HistoricoResposta(BaseModel):
    estado: str
    descricao: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoResposta(BaseModel):
    id: str
    cliente_id: str
    estado: str
    total: Decimal
    motivo_cancelamento: str | None
    criado_em: datetime
    atualizado_em: datetime
    itens: list[ItemPedidoResposta]
    historico: list[HistoricoResposta]

    model_config = ConfigDict(from_attributes=True)


class PedidoAceito(BaseModel):
    id: str
    estado: str
    mensagem: str
