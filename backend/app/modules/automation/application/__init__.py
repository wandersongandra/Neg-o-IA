"""Automation V1 — regras internas seguras disparadas por eventos allowlisted."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.automation.domain import AutomationExecution, AutomationRule
from app.modules.automation.infrastructure import PostgresAutomationRuleStore
from app.modules.events.envelope import EventEnvelope, build_envelope
from app.modules.tool_manager.application import get_tool_manager_service

_LOGGER = logging.getLogger("app.modules.automation.application")
PRODUCER = "automation"

AUTOMATION_TRIGGER_EVENTS: frozenset[str] = frozenset(
    {
        "conversation.message.responded",
        "memory.long_term.written",
        "knowledge.document.ingested",
    }
)

_service: AutomationService | None = None
_handlers_registered = False


def _resolve_event_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"unknown event field: {path}")
        current = current[part]
    return current


def resolve_action_args(value: Any, payload: dict[str, Any]) -> Any:
    """Resolve apenas templates explícitos '$event.campo'; não avalia código."""
    if isinstance(value, str) and value.startswith("$event."):
        return _resolve_event_path(payload, value.removeprefix("$event."))
    if isinstance(value, dict):
        return {key: resolve_action_args(item, payload) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_action_args(item, payload) for item in value]
    return value


class AutomationService:
    def __init__(self, store: PostgresAutomationRuleStore | None = None) -> None:
        self._store = store or PostgresAutomationRuleStore()

    async def create_rule(
        self,
        user_id: str,
        *,
        name: str,
        event_type: str,
        action_tool: str,
        action_args: dict[str, Any],
        enabled: bool = True,
    ) -> AutomationRule:
        normalized_name = name.strip()
        if not normalized_name or len(normalized_name) > 160:
            raise ValueError("name must contain 1..160 characters")
        if event_type not in AUTOMATION_TRIGGER_EVENTS:
            raise ValueError("event type is not allowed for automation")

        spec = get_tool_manager_service().get_spec(action_tool)
        if spec is None:
            raise ValueError("unknown tool")
        if not spec.automation_safe or spec.requires_confirmation:
            raise ValueError("tool is not safe for unattended automation")

        return await self._store.create(
            user_id,
            name=normalized_name,
            event_type=event_type,
            action_tool=action_tool,
            action_args=action_args,
            enabled=enabled,
        )

    async def list_rules(self, user_id: str) -> list[AutomationRule]:
        return await self._store.list_for_user(user_id)

    async def set_enabled(
        self,
        user_id: str,
        rule_id: str,
        *,
        enabled: bool,
    ) -> AutomationRule | None:
        return await self._store.set_enabled(user_id, rule_id, enabled=enabled)

    async def delete_rule(self, user_id: str, rule_id: str) -> bool:
        return await self._store.delete(user_id, rule_id)

    async def evaluate_rules(
        self,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[AutomationExecution]:
        if event_type not in AUTOMATION_TRIGGER_EVENTS:
            return []

        executions: list[AutomationExecution] = []
        rules = await self._store.list_for_event(user_id, event_type)
        tools = get_tool_manager_service()

        for rule in rules:
            spec = tools.get_spec(rule.action_tool)
            if spec is None or not spec.automation_safe or spec.requires_confirmation:
                _LOGGER.warning(
                    "automation_rule_blocked",
                    extra={"rule_id": rule.id, "tool_name": rule.action_tool},
                )
                continue
            try:
                arguments = resolve_action_args(rule.action_args, payload)
                if not isinstance(arguments, dict):
                    raise ValueError("automation action arguments must resolve to an object")
                result = await tools.execute_tool(
                    rule.action_tool,
                    arguments,
                    user_id=user_id,
                    confirmed=False,
                    idempotency_key=f"automation:{rule.id}:{payload.get('event_id', '')}",
                )
                await self._store.mark_triggered(user_id, rule.id)
                execution = AutomationExecution(
                    rule_id=rule.id,
                    tool_name=result.tool_name,
                    output=result.output,
                )
                executions.append(execution)
                await self._publish(
                    "automation.rule.triggered",
                    user_id,
                    {
                        "rule_id": rule.id,
                        "tool_name": result.tool_name,
                    },
                )
            except Exception:
                _LOGGER.warning(
                    "automation_rule_execution_failed",
                    extra={"rule_id": rule.id, "tool_name": rule.action_tool},
                    exc_info=True,
                )
        return executions

    async def handle_event(self, envelope: EventEnvelope) -> None:
        if envelope.type not in AUTOMATION_TRIGGER_EVENTS or not envelope.user_id:
            return
        payload = {"event_id": envelope.id, **envelope.payload}
        await self.evaluate_rules(envelope.user_id, envelope.type, payload)

    async def _publish(
        self,
        event_type: str,
        user_id: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    payload,
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("automation_event_publish_failed", exc_info=True)


def get_automation_service() -> AutomationService:
    global _service
    if _service is None:
        _service = AutomationService()
    return _service


def register_automation_handlers(event_bus_service: Any) -> None:
    global _handlers_registered
    if _handlers_registered:
        return
    service = get_automation_service()
    for event_type in AUTOMATION_TRIGGER_EVENTS:
        event_bus_service.register_handler(event_type, service.handle_event)
    _handlers_registered = True
