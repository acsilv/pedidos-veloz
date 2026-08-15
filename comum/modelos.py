from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


class CamposOutbox:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conteudo: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CamposEventoProcessado:
    id_evento: Mapped[str] = mapped_column(String(36), primary_key=True)
    processado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
