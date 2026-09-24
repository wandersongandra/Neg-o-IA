"use client";

import { useState } from "react";
import { CheckCircle2, Play, RefreshCw } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface PlanStep {
  step_id: string;
  kind: string;
  description: string;
  tool_name: string | null;
  requires_confirmation: boolean;
}

interface Plan {
  plan_id: string;
  goal: string;
  intent: string;
  revision: number;
  steps: PlanStep[];
}

interface StepExecution {
  step_id: string;
  status: string;
  tool_name: string | null;
  output?: Record<string, unknown> | null;
  error?: string | null;
}

interface ExecutionResult {
  plan_id: string;
  revision: number;
  status: string;
  steps: StepExecution[];
}

export default function PlannerPage() {
  const [goal, setGoal] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [execution, setExecution] = useState<ExecutionResult | null>(null);
  const [failureReason, setFailureReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function createPlan() {
    if (!goal.trim()) return;
    setBusy(true);
    setMessage(null);
    setExecution(null);
    try {
      const res = await fetch("/api/proxy/planner/plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: goal.trim() }),
      });
      if (!res.ok) throw new Error("Falha ao criar plano");
      setPlan((await res.json()) as Plan);
      setConfirmed({});
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao criar plano");
    } finally {
      setBusy(false);
    }
  }

  async function executePlan() {
    if (!plan) return;
    setBusy(true);
    setMessage(null);
    try {
      const confirmedStepIds = Object.entries(confirmed)
        .filter(([, value]) => value)
        .map(([key]) => key);
      const res = await fetch(`/api/proxy/planner/plans/${plan.plan_id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed_step_ids: confirmedStepIds }),
      });
      if (!res.ok) throw new Error("Falha ao executar plano");
      setExecution((await res.json()) as ExecutionResult);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao executar plano");
    } finally {
      setBusy(false);
    }
  }

  async function replan() {
    if (!plan || !failureReason.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch(`/api/proxy/planner/plans/${plan.plan_id}/replan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: failureReason.trim() }),
      });
      if (!res.ok) throw new Error("Falha ao replanejar");
      setPlan((await res.json()) as Plan);
      setExecution(null);
      setConfirmed({});
      setFailureReason("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao replanejar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell
      title="Planner"
      description="Planos limitados, auditáveis e executados somente por ferramentas allowlisted."
    >
      <section className="glass rounded-2xl p-5">
        <label className="block text-sm font-medium">Objetivo</label>
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          rows={4}
          maxLength={4000}
          placeholder="Ex.: procure na memória informações sobre o projeto atual."
          className="mt-2 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none"
        />
        <button
          type="button"
          onClick={() => void createPlan()}
          disabled={busy || !goal.trim()}
          className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
        >
          Criar plano
        </button>
      </section>

      {plan ? (
        <section className="glass rounded-2xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">{plan.goal}</h2>
              <p className="font-mono-data text-[10px] text-[var(--text-secondary)]">
                intenção {plan.intent} · revisão {plan.revision}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void executePlan()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-xl border border-[var(--accent)]/30 px-4 py-2.5 text-sm text-[var(--accent)] disabled:opacity-50"
            >
              <Play className="size-4" />
              Executar plano
            </button>
          </div>

          <div className="mt-4 space-y-3">
            {plan.steps.map((step, index) => (
              <div key={step.step_id} className="rounded-xl border border-[var(--border)] p-4">
                <div className="flex items-start gap-3">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-muted)] font-mono-data text-xs text-[var(--accent)]">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{step.description}</p>
                    <p className="mt-1 font-mono-data text-[10px] text-[var(--text-secondary)]">
                      {step.kind}{step.tool_name ? ` · ${step.tool_name}` : ""}
                    </p>
                    {step.requires_confirmation ? (
                      <label className="mt-3 flex items-center gap-2 text-xs text-[var(--color-warn)]">
                        <input
                          type="checkbox"
                          checked={Boolean(confirmed[step.step_id])}
                          onChange={(event) =>
                            setConfirmed((current) => ({
                              ...current,
                              [step.step_id]: event.target.checked,
                            }))
                          }
                        />
                        Confirmo explicitamente esta etapa de escrita
                      </label>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <input
              value={failureReason}
              onChange={(event) => setFailureReason(event.target.value)}
              placeholder="Motivo para replanejar, se necessário"
              maxLength={500}
              className="min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm outline-none"
            />
            <button
              type="button"
              onClick={() => void replan()}
              disabled={busy || !failureReason.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--border)] px-4 py-2.5 text-sm disabled:opacity-50"
            >
              <RefreshCw className="size-4" />
              Replanejar
            </button>
          </div>
        </section>
      ) : null}

      {execution ? (
        <section className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-4 text-[var(--accent)]" />
            <h2 className="font-semibold">Execução: {execution.status}</h2>
          </div>
          <div className="mt-4 space-y-3">
            {execution.steps.map((step) => (
              <div key={step.step_id} className="rounded-xl border border-[var(--border)] p-3">
                <p className="text-sm">
                  Etapa {step.step_id}: <strong>{step.status}</strong>
                </p>
                {step.output ? (
                  <pre className="mt-2 overflow-auto text-xs text-[var(--text-secondary)]">
                    {JSON.stringify(step.output, null, 2)}
                  </pre>
                ) : null}
                {step.error ? <p className="mt-2 text-xs text-[var(--color-danger)]">{step.error}</p> : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {message ? <p className="text-sm text-[var(--color-warn)]">{message}</p> : null}
    </WorkspaceShell>
  );
}
