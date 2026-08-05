"""Camada de aplicação do módulo monitoring — MonitoringService (facade)."""

from __future__ import annotations

from app.modules.monitoring.infrastructure import (
    active_connections_set,
    event_published_observed,
    http_request_observed,
    negao_metrics,
)

_monitoring_service: MonitoringService | None = None


class MonitoringService:
    """Facade de observabilidade: métricas, logs estruturados e snapshots."""

    def record_request(self, method: str, path: str, status: int, duration: float) -> None:
        http_request_observed(method, path, status, duration)

    def record_event_published(self, event_type: str) -> None:
        event_published_observed(event_type)

    def set_active_connections(self, value: int) -> None:
        active_connections_set(value)

    def get_snapshot(self) -> bytes:
        """Exporta as métricas Prometheus (formato text exposition)."""
        try:
            from prometheus_client import generate_latest

            return generate_latest()
        except Exception:
            return b""

    @property
    def metrics_available(self) -> bool:
        return bool(negao_metrics)


def get_monitoring_service() -> MonitoringService:
    """Singleton do MonitoringService."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
