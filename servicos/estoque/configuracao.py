from functools import lru_cache

from comum.configuracao import ConfiguracaoBase


class ConfiguracaoEstoque(ConfiguracaoBase):
    nome_servico: str = "estoque"
    porta: int = 8002
    banco_url: str = "postgresql+psycopg://veloz:troque-esta-senha@postgres:5432/estoque"
    fila_eventos: str = "estoque.eventos"


@lru_cache
def obter_configuracao() -> ConfiguracaoEstoque:
    return ConfiguracaoEstoque()
