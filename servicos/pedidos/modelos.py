from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from comum.modelos import CamposEventoProcessado, CamposOutbox


class Base(DeclarativeBase):
    pass


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    token_pagamento: Mapped[str] = mapped_column(String(120), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", lazy="selectin"
    )
    historico: Mapped[list["HistoricoPedido"]] = relationship(
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="HistoricoPedido.criado_em",
    )


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(60), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pedido: Mapped[Pedido] = relationship(back_populates="itens")


class HistoricoPedido(Base):
    __tablename__ = "historico_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(40), nullable=False)
    descricao: Mapped[str] = mapped_column(String(240), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pedido: Mapped[Pedido] = relationship(back_populates="historico")


class EventoOutbox(CamposOutbox, Base):
    __tablename__ = "eventos_outbox"


class EventoProcessado(CamposEventoProcessado, Base):
    __tablename__ = "eventos_processados"
