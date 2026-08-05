"""Implementação da observabilidade (v0): structlog, Prometheus e OpenTelemetry.

`setup_observability` é idempotente: pode ser chamada várias vezes no boot.
Dependências opcionais (structlog/prometheus_client/OTel) degradam com warning.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_LOGGER = logging.getLogger("app.modules.monitoring")

_observability_ready = False

negao_metrics: dict[str, Any] = {}


def _add_process_info(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict["process"] = os.getpid()
    return event_dict


def setup_observability(settings: Any, *, fastapi_app: Any | None = None) -> None:
    """Configura logs estruturados, métricas Prometheus e tracing OTLP (1x)."""
    global _observability_ready
    if _observability_ready:
        return
    _setup_structured_logging(settings)
    _setup_prometheus_metrics()
    _setup_tracing(settings, fastapi_app)
    _observability_ready = True


def setup_telemetry(settings: Any) -> None:
    """Alias de boot usado pelo main.py (idempotente)."""
    setup_observability(settings, fastapi_app=None)


def _setup_structured_logging(settings: Any) -> None:
    try:
        import structlog
    except Exception as exc:
        _LOGGER.warning(
            "structlog indisponível — usando logging padrão", extra={"error": str(exc)}
        )
        return
    debug = bool(getattr(settings, "debug", False))
    common_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_process_info,
    ]
    if debug:
        processors = [
            *common_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *common_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )
    _LOGGER.info("structlog configurado", extra={"json": not debug})


def _setup_prometheus_metrics() -> None:
    if "requests_total" in negao_metrics:
        return
    try:
        from prometheus_client import Counter, Gauge, Histogram
    except Exception as exc:
        _LOGGER.warning(
            "prometheus_client indisponível — métricas desativadas",
            extra={"error": str(exc)},
        )
        return
    negao_metrics["requests_total"] = Counter(
        "negao_requests_total",
        "Requisições HTTP recebidas",
        ["method", "path", "status"],
    )
    negao_metrics["request_duration_seconds"] = Histogram(
        "negao_request_duration_seconds",
        "Duração das requisições HTTP",
        ["method", "path"],
    )
    negao_metrics["active_connections"] = Gauge(
        "negao_active_connections", "Conexões ativas"
    )
    negao_metrics["events_published_total"] = Counter(
        "negao_events_published_total",
        "Eventos publicados no barramento",
        ["event_type"],
    )


def _setup_tracing(settings: Any, fastapi_app: Any | None) -> None:
    endpoint = getattr(settings, "otel_exporter_otlp_endpoint", None)
    if not endpoint:
        return
    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:
        _LOGGER.warning(
            "OpenTelemetry indisponível — tracing desativado",
            extra={"error": str(exc)},
        )
        return
    try:
        resource = Resource.create({"service.name": "negao-ai"})
        provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        otel_trace.set_tracer_provider(provider)
        if fastapi_app is not None:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(fastapi_app)
        negao_metrics["tracer_provider"] = provider
        _LOGGER.info("OpenTelemetry inicializado", extra={"endpoint": endpoint})
    except Exception as exc:
        _LOGGER.warning(
            "falha ao inicializar OpenTelemetry",
            extra={"error": str(exc)},
        )


def http_request_observed(method: str, path: str, status: int, duration: float) -> None:
    """Registra uma requisição HTTP no Counter e no Histogram."""
    counter = negao_metrics.get("requests_total")
    histogram = negao_metrics.get("request_duration_seconds")
    if counter is None or histogram is None:
        return
    counter.labels(method=method, path=path, status=str(status)).inc()
    histogram.labels(method=method, path=path).observe(duration)


def event_published_observed(event_type: str) -> None:
    """Incrementa o contador de eventos publicados por tipo."""
    counter = negao_metrics.get("events_published_total")
    if counter is None:
        return
    counter.labels(event_type=event_type).inc()


def active_connections_set(value: int) -> None:
    """Define o gauge de conexões ativas."""
    gauge = negao_metrics.get("active_connections")
    if gauge is not None:
        gauge.set(value)
