import json
import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, make_asgi_app

REQUISICOES = Counter(
    "http_requisicoes_total",
    "Quantidade de requisições HTTP",
    ["servico", "metodo", "rota", "status"],
)
DURACAO = Histogram(
    "http_duracao_segundos",
    "Duração das requisições HTTP",
    ["servico", "metodo", "rota"],
)


class FormatadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        contexto = trace.get_current_span().get_span_context()
        corpo: dict[str, Any] = {
            "horario": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        if contexto.is_valid:
            corpo["trace_id"] = format(contexto.trace_id, "032x")
            corpo["span_id"] = format(contexto.span_id, "016x")
        if record.exc_info:
            corpo["erro"] = self.formatException(record.exc_info)
        return json.dumps(corpo, ensure_ascii=False)


def configurar_logs(nivel: str) -> None:
    manipulador = logging.StreamHandler()
    manipulador.setFormatter(FormatadorJson())
    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.addHandler(manipulador)
    raiz.setLevel(nivel.upper())


def configurar_tracing(nome_servico: str, endpoint: str) -> None:
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    provedor = TracerProvider(resource=Resource.create({"service.name": nome_servico}))
    provedor.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provedor)
    HTTPXClientInstrumentor().instrument()


def preparar_observabilidade(app: FastAPI, nome_servico: str, endpoint_otel: str) -> None:
    configurar_tracing(nome_servico, endpoint_otel)
    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def medir_requisicao(
        request: Request,
        chamar_proximo: Callable[[Request], Any],
    ) -> Response:
        inicio = time.perf_counter()
        resposta: Response = await chamar_proximo(request)
        rota = getattr(request.scope.get("route"), "path", request.url.path)
        DURACAO.labels(nome_servico, request.method, rota).observe(time.perf_counter() - inicio)
        REQUISICOES.labels(nome_servico, request.method, rota, resposta.status_code).inc()
        return resposta

    app.mount("/metricas", make_asgi_app())
