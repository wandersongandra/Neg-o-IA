"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, Power, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface Rule {
  id: string;
  name: string;
  event_type: string;
  action_tool: string;
  action_args: Record<string, unknown>;
  enabled: boolean;
  last_triggered_at: string | null;
}
interface Tool {
  name: string;
  description: string;
  automation_safe: boolean;
  requires_confirmation: boolean;
}

export default function AutomationPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [name, setName] = useState("");
  const [eventType, setEventType] = useState("");
  const [toolName, setToolName] = useState("");
  const [args, setArgs] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [rulesRes, capRes, toolsRes] = await Promise.all([
      fetch("/api/proxy/automation/rules", { cache: "no-store" }),
      fetch("/api/proxy/automation/capabilities", { cache: "no-store" }),
      fetch("/api/proxy/tool-manager/catalog", { cache: "no-store" }),
    ]);
    if (rulesRes.ok) setRules(((await rulesRes.json()) as { rules?: Rule[] }).rules ?? []);
    if (capRes.ok) {
      const next = ((await capRes.json()) as { trigger_events?: string[] }).trigger_events ?? [];
      setEvents(next);
      setEventType((current) => current || next[0] || "");
    }
    if (toolsRes.ok) {
      const next = (((await toolsRes.json()) as { tools?: Tool[] }).tools ?? []).filter(
        (tool) => tool.automation_safe && !tool.requires_confirmation,
      );
      setTools(next);
      setToolName((current) => current || next[0]?.name || "");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function createRule() {
    setError(null);
    try {
      const parsed = JSON.parse(args) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
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
      if (!res.ok) throw new Error();
      setName("");
      setArgs("{}");
      await load();
    } catch {
      setError("Regra inválida. Verifique nome, ferramenta e JSON de argumentos.");
    }
  }

  async function setEnabled(rule: Rule) {
    const res = await fetch(`/api/proxy/automation/rules/${rule.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !rule.enabled }),
    });
    if (res.ok) await load();
  }

  async function remove(id: string) {
    const res = await fetch(`/api/proxy/automation/rules/${id}`, { method: "DELETE" });
    if (res.ok) await load();
  }

  return (
    <WorkspaceShell title="Automações">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">EVENT AUTOMATION</p>
        <h1 className="mt-2 text-3xl font-semibold">Automações seguras</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Somente ferramentas marcadas como automation-safe podem rodar sem confirmação.</p>
      </header>

      <section className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2"><Bot className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Nova regra</h2></div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome da regra" className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
          <select value={eventType} onChange={(e) => setEventType(e.target.value)} className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm">{events.map((item) => <option key={item}>{item}</option>)}</select>
          <select value={toolName} onChange={(e) => setToolName(e.target.value)} className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm">{tools.map((tool) => <option key={tool.name} value={tool.name}>{tool.name}</option>)}</select>
          <input value={args} onChange={(e) => setArgs(e.target.value)} placeholder='{"query":"$event.text"}' className="font-mono-data rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
        </div>
        {error ? <p className="mt-3 text-sm text-[var(--color-danger)]">{error}</p> : null}
        <button type="button" onClick={() => void createRule()} disabled={!name.trim() || !eventType || !toolName} className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">Criar regra</button>
      </section>

      <section className="space-y-3">
        {rules.length === 0 ? <div className="glass rounded-2xl p-8 text-center text-sm text-[var(--text-secondary)]">Nenhuma automação configurada.</div> : rules.map((rule) => (
          <article key={rule.id} className="glass rounded-2xl p-4">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1"><h2 className="font-medium">{rule.name}</h2><p className="mt-1 font-mono-data text-[10px] text-[var(--text-secondary)]">{rule.event_type} → {rule.action_tool}</p><p className="mt-2 text-xs text-[var(--text-secondary)]">{rule.last_triggered_at ? `Último disparo: ${new Date(rule.last_triggered_at).toLocaleString("pt-BR")}` : "Ainda não disparada"}</p></div>
              <button type="button" onClick={() => void setEnabled(rule)} className={`rounded-lg p-2 ${rule.enabled ? "text-[var(--color-ok)]" : "text-[var(--text-secondary)]"}`} aria-label={rule.enabled ? "Desativar regra" : "Ativar regra"}><Power className="size-4" /></button>
              <button type="button" onClick={() => void remove(rule.id)} className="rounded-lg p-2 text-[var(--color-danger)]" aria-label="Excluir regra"><Trash2 className="size-4" /></button>
            </div>
          </article>
        ))}
      </section>
    </WorkspaceShell>
  );
}
