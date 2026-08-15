from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventoDominio(BaseModel):
    id_evento: str = Field(default_factory=lambda: str(uuid4()))
    tipo: str
    versao: int = 1
    ocorrido_em: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlacao_id: str
    dados: dict[str, Any]

    model_config = ConfigDict(extra="forbid")

    def para_json(self) -> str:
        return self.model_dump_json()


def novo_evento(tipo: str, correlacao_id: str, dados: dict[str, Any]) -> EventoDominio:
    return EventoDominio(tipo=tipo, correlacao_id=correlacao_id, dados=dados)
