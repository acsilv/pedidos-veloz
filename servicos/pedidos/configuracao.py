from functools import lru_cache

from comum.configuracao import ConfiguracaoBase


class ConfiguracaoPedidos(ConfiguracaoBase):
    nome_servico: str = "pedidos"
    porta: int = 8001
    banco_url: str = "postgresql+psycopg://veloz:troque-esta-senha@postgres:5432/pedidos"
    fila_resultados: str = "pedidos.resultados"


@lru_cache
def obter_configuracao() -> ConfiguracaoPedidos:
    return ConfiguracaoPedidos()
