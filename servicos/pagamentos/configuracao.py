from functools import lru_cache

from comum.configuracao import ConfiguracaoBase


class ConfiguracaoPagamentos(ConfiguracaoBase):
    nome_servico: str = "pagamentos"
    porta: int = 8003
    banco_url: str = "postgresql+psycopg://veloz:troque-esta-senha@postgres:5432/pagamentos"
    fila_eventos: str = "pagamentos.eventos"


@lru_cache
def obter_configuracao() -> ConfiguracaoPagamentos:
    return ConfiguracaoPagamentos()
