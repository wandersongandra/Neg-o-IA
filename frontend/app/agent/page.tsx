"use client";

import { useState } from "react";
import { BrainCircuit, Play, Route, Wrench } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface IntentResult {
  intent: string;
  confidence: number;
  requires_plan: boolean;
  suggested_tool: string | null;
  explicit_action: boolean;
  entities: Record<string, unknown>;
}
interface PlanResult {
  plan_id: string;
  goal: string;
  intent: string;
  revision: number;
  steps: Array<{
    step_id: string;
    kind: string;
    description: string;
    tool_name: string | null;
    requires_confirmation: boolean;
  }>;
}
interface ToolSpec {
  name: string;
  description: string;
  risk: string;
  requires_confirmation: boolean;
  automation_safe: boolean;
}

export default function AgentPage() {
  const [text, setText] = useState("");
  const [intent, setIntent] = useState<IntentResult | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [busy, setBusy] = useState(false);

  async function inspect() {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const [intentRes, planRes, toolsRes] = await Promise.all([
        fetch("/api/proxy/reasoning/resolve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text.trim() }),
        }),
        fetch("/api/proxy/planner/plans", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text.trim() }),
        }),
        fetch("/api/proxy/tool-manager/catalog", { cache: "no-store" }),
      ]);
      if (intentRes.ok) setIntent((await intentRes.json()) as IntentResult);
      if (planRes.ok) setPlan((await planRes.json()) as PlanResult);
      if (toolsRes.ok) {
        const body = (await toolsRes.json()) as { tools?: ToolSpec[] };
        setTools(body.tools ?? []);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell title="Agente">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">AGENT CORE</p>
        <h1 className="mt-2 text-3xl font-semibold">Reasoning, Planner e Tools</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Inspecione como a Sophie interpreta um objetivo antes de executar qualquer ferramenta.
        </p>
      </header>

      <section className="glass rounded-2xl p-5">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} maxLength={4000} placeholder="Ex.: procure na memória o que eu disse sobre o projeto SGS" className="w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
        <button type="button" onClick={() => void inspect()} disabled={busy || !text.trim()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"><Play className="size-4" />Analisar objetivo</button>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2"><BrainCircuit className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Intent Resolution</h2></div>
          {intent ? (
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-[var(--text-secondary)]">Intent</dt><dd>{intent.intent}</dd></div>
              <div><dt className="text-[var(--text-secondary)]">Confiança</dt><dd>{intent.confidence.toFixed(2)}</dd></div>
              <div><dt className="text-[var(--text-secondary)]">Ferramenta</dt><dd>{intent.suggested_tool ?? "nenhuma"}</dd></div>
              <div><dt className="text-[var(--text-secondary)]">Ação explícita</dt><dd>{intent.explicit_action ? "sim" : "não"}</dd></div>
            </dl>
          ) : <p className="mt-4 text-sm text-[var(--text-secondary)]">Nenhuma intenção analisada ainda.</p>}
        </section>

        <section className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2"><Route className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Execution Plan</h2></div>
          <div className="mt-4 space-y-2">
            {plan?.steps.map((step) => (
              <div key={step.step_id} className="rounded-xl border border-[var(--border)] p-3 text-sm">
                <div className="flex items-center justify-between gap-2"><span className="font-medium">{step.description}</span><span className="font-mono-data text-[10px] text-[var(--accent)]">{step.kind}</span></div>
                {step.tool_name ? <p className="mt-1 text-xs text-[var(--text-secondary)]">{step.tool_name}{step.requires_confirmation ? " · confirmação obrigatória" : ""}</p> : null}
              </div>
            )) ?? <p className="text-sm text-[var(--text-secondary)]">Nenhum plano criado ainda.</p>}
          </div>
        </section>
      </div>

      <section className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2"><Wrench className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Catálogo de ferramentas</h2></div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {tools.map((tool) => (
            <div key={tool.name} className="rounded-xl border border-[var(--border)] p-3">
              <p className="font-mono-data text-xs text-[var(--accent)]">{tool.name}</p>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{tool.description}</p>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">{tool.risk} · {tool.automation_safe ? "automation-safe" : "manual"}{tool.requires_confirmation ? " · confirmação" : ""}</p>
            </div>
          ))}
        </div>
      </section>
    </WorkspaceShell>
  );
}
