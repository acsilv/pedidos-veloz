from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from comum.modelos import CamposEventoProcessado, CamposOutbox


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    sku: Mapped[str] = mapped_column(String(60), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    quantidade_disponivel: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade_reservada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Reserva(Base):
    __tablename__ = "reservas"

    pedido_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    itens: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventoOutbox(CamposOutbox, Base):
    __tablename__ = "eventos_outbox"


class EventoProcessado(CamposEventoProcessado, Base):
    __tablename__ = "eventos_processados"
