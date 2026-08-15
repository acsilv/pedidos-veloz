from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracaoBase(BaseSettings):
    nome_servico: str
    porta: int = 8000
    nivel_log: str = "INFO"
    ambiente: str = "desenvolvimento"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    banco_url: str = ""
    rabbitmq_url: str = "amqp://veloz:troque-esta-senha@rabbitmq:5672/"
    exchange_eventos: str = "pedidos.eventos"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def obter_configuracao_base() -> ConfiguracaoBase:
    return ConfiguracaoBase(nome_servico="servico")
