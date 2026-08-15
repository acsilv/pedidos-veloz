from functools import lru_cache

from comum.configuracao import ConfiguracaoBase


class ConfiguracaoGateway(ConfiguracaoBase):
    nome_servico: str = "gateway"
    porta: int = 8000
    url_pedidos: str = "http://pedidos:8001"
    url_estoque: str = "http://estoque:8002"
    tempo_limite_segundos: float = 5.0


@lru_cache
def obter_configuracao() -> ConfiguracaoGateway:
    return ConfiguracaoGateway()
