from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from comum.modelos import CamposEventoProcessado, CamposOutbox


class Base(DeclarativeBase):
    pass


class Pagamento(Base):
    __tablename__ = "pagamentos"

    pedido_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(36), nullable=True)
    final_token: Mapped[str] = mapped_column(String(4), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(180), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventoOutbox(CamposOutbox, Base):
    __tablename__ = "eventos_outbox"


class EventoProcessado(CamposEventoProcessado, Base):
    __tablename__ = "eventos_processados"
