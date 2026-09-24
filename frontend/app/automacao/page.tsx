"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface AutomationRule {
  id: string;
  name: string;
  event_type: string;
  action_tool: string;
  action_args: Record<string, unknown>;
  enabled: boolean;
  last_triggered_at: string | null;
}

interface ToolSpec {
  name: string;
  automation_safe: boolean;
  requires_confirmation: boolean;
}

export default function AutomationPage() {
  const [events, setEvents] = useState<string[]>([]);
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [name, setName] = useState("");
  const [eventType, setEventType] = useState("");
  const [toolName, setToolName] = useState("");
  const [argsText, setArgsText] = useState("{}");
  const [message, setMessage] = useState<string | null>(null);

  const safeTools = useMemo(
    () => tools.filter((tool) => tool.automation_safe && !tool.requires_confirmation),
    [tools],
  );

  async function load() {
    const [capsRes, toolsRes, rulesRes] = await Promise.all([
      fetch("/api/proxy/automation/capabilities", { cache: "no-store" }),
      fetch("/api/proxy/tool-manager/catalog", { cache: "no-store" }),
      fetch("/api/proxy/automation/rules", { cache: "no-store" }),
    ]);
    if (capsRes.ok) {
      const data = (await capsRes.json()) as { trigger_events?: string[] };
      const values = data.trigger_events ?? [];
      setEvents(values);
      setEventType((current) => current || values[0] || "");
    }
    if (toolsRes.ok) {
      const data = (await toolsRes.json()) as { tools?: ToolSpec[] };
      const values = data.tools ?? [];
      setTools(values);
      const firstSafe = values.find(
        (tool) => tool.automation_safe && !tool.requires_confirmation,
      );
      if (firstSafe) setToolName((current) => current || firstSafe.name);
    }
    if (rulesRes.ok) {
      const data = (await rulesRes.json()) as { rules?: AutomationRule[] };
      setRules(data.rules ?? []);
    }
  }

  useEffect(() => {
    void load().catch(() => setMessage("Não foi possível carregar as automações."));
  }, []);

  async function createRule() {
    if (!name.trim() || !eventType || !toolName) return;
    try {
      const parsed = JSON.parse(argsText) as unknown;
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("action_args precisa ser um objeto JSON.");
      }
      const res = await fetch("/api/proxy/automation/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          event_type: eventType,
          action_tool: toolName,
          action_args: parsed,
          enabled: true,
        }),
      });
      if (!res.ok) throw new Error("A regra foi rejeitada pelo backend.");
      setName("");
      setArgsText("{}");
      setMessage("Regra criada.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao criar regra");
    }
  }

  async function toggle(rule: AutomationRule) {
    await fetch(`/api/proxy/automation/rules/${rule.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !rule.enabled }),
    });
    await load();
  }

  async function remove(rule: AutomationRule) {
    if (!window.confirm(`Excluir a automação "${rule.name}"?`)) return;
    await fetch(`/api/proxy/automation/rules/${rule.id}`, { method: "DELETE" });
    await load();
  }

  return (
    <WorkspaceShell
      title="Automação"
      description="Regras internas por evento. Somente ferramentas marcadas como seguras para execução autônoma são aceitas."
    >
      <section className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-[var(--accent)]" />
          <h2 className="font-semibold">Nova regra</h2>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={160}
            placeholder="Nome da regra"
            className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm outline-none"
          />
          <select
            value={eventType}
            onChange={(event) => setEventType(event.target.value)}
            className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm"
          >
            {events.map((event) => <option key={event} value={event}>{event}</option>)}
          </select>
          <select
            value={toolName}
            onChange={(event) => setToolName(event.target.value)}
            className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm"
          >
            {safeTools.map((tool) => <option key={tool.name} value={tool.name}>{tool.name}</option>)}
          </select>
          <textarea
            value={argsText}
            onChange={(event) => setArgsText(event.target.value)}
            rows={3}
            spellCheck={false}
            className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 font-mono-data text-xs outline-none"
            placeholder='{"query":"$event.algum_campo"}'
          />
        </div>
        <button
          type="button"
          onClick={() => void createRule()}
          className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black"
        >
          Criar regra
        </button>
        {message ? <p className="mt-3 text-sm text-[var(--text-secondary)]">{message}</p> : null}
      </section>

      <section className="glass rounded-2xl p-5">
        <h2 className="font-semibold">Regras ativas</h2>
        <div className="mt-4 space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="rounded-xl border border-[var(--border)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{rule.name}</p>
                  <p className="mt-1 font-mono-data text-[10px] text-[var(--text-secondary)]">
                    {rule.event_type} → {rule.action_tool}
                  </p>
                  {rule.last_triggered_at ? (
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Última execução: {new Date(rule.last_triggered_at).toLocaleString("pt-BR")}
                    </p>
                  ) : null}
                </div>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={() => void toggle(rule)}
                    />
                    ativa
                  </label>
                  <button
                    type="button"
                    onClick={() => void remove(rule)}
                    className="text-[var(--color-danger)]"
                    aria-label={`Excluir ${rule.name}`}
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </div>
              <pre className="mt-3 overflow-auto rounded-lg bg-black/20 p-2 font-mono-data text-[10px] text-[var(--text-secondary)]">
                {JSON.stringify(rule.action_args, null, 2)}
              </pre>
            </div>
          ))}
          {rules.length === 0 ? (
            <p className="text-sm text-[var(--text-secondary)]">Nenhuma regra criada.</p>
          ) : null}
        </div>
      </section>
    </WorkspaceShell>
  );
}
