from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PagamentoResposta(BaseModel):
    pedido_id: str
    estado: str
    valor: Decimal
    referencia: str | None
    final_token: str
    motivo: str | None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
