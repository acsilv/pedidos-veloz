from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProdutoResposta(BaseModel):
    sku: str
    nome: str
    quantidade_disponivel: int
    quantidade_reservada: int
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)
