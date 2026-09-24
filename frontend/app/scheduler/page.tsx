"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarClock, Power, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface Job {
  id: string;
  name: string;
  action_tool: string;
  action_args: Record<string, unknown>;
  interval_seconds: number | null;
  enabled: boolean;
  next_run_at: string;
  last_run_at: string | null;
}
interface Tool {
  name: string;
  automation_safe: boolean;
  requires_confirmation: boolean;
}

export default function SchedulerPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [name, setName] = useState("");
  const [toolName, setToolName] = useState("");
  const [args, setArgs] = useState("{}");
  const [runAt, setRunAt] = useState("");
  const [intervalMinutes, setIntervalMinutes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [jobsRes, toolsRes] = await Promise.all([
      fetch("/api/proxy/scheduler/jobs", { cache: "no-store" }),
      fetch("/api/proxy/tool-manager/catalog", { cache: "no-store" }),
    ]);
    if (jobsRes.ok) setJobs(((await jobsRes.json()) as { jobs?: Job[] }).jobs ?? []);
    if (toolsRes.ok) {
      const safe = (((await toolsRes.json()) as { tools?: Tool[] }).tools ?? []).filter(
        (tool) => tool.automation_safe && !tool.requires_confirmation,
      );
      setTools(safe);
      setToolName((current) => current || safe[0]?.name || "");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function createJob() {
    setError(null);
    try {
      const parsed = JSON.parse(args) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
      const date = new Date(runAt);
      if (Number.isNaN(date.getTime())) throw new Error();
      const minutes = intervalMinutes.trim() ? Number(intervalMinutes) : null;
      const res = await fetch("/api/proxy/scheduler/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          action_tool: toolName,
          action_args: parsed,
          run_at: date.toISOString(),
          interval_seconds: minutes ? Math.round(minutes * 60) : null,
        }),
      });
      if (!res.ok) throw new Error();
      setName("");
      setArgs("{}");
      setRunAt("");
      setIntervalMinutes("");
      await load();
    } catch {
      setError("Agendamento inválido. Use uma data futura e argumentos JSON válidos.");
    }
  }

  async function setEnabled(job: Job) {
    const res = await fetch(`/api/proxy/scheduler/jobs/${job.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !job.enabled }),
    });
    if (res.ok) await load();
  }

  async function remove(id: string) {
    const res = await fetch(`/api/proxy/scheduler/jobs/${id}`, { method: "DELETE" });
    if (res.ok) await load();
  }

  return (
    <WorkspaceShell title="Agendamentos">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">SCHEDULER V1</p>
        <h1 className="mt-2 text-3xl font-semibold">Agendamentos persistentes</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Jobs sobrevivem a reinícios e só podem executar ferramentas automation-safe.</p>
      </header>

      <section className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2"><CalendarClock className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Novo job</h2></div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome" className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
          <select value={toolName} onChange={(e) => setToolName(e.target.value)} className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm">{tools.map((tool) => <option key={tool.name}>{tool.name}</option>)}</select>
          <label className="text-sm text-[var(--text-secondary)]">Executar em<input type="datetime-local" value={runAt} onChange={(e) => setRunAt(e.target.value)} className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-[var(--text-primary)]" /></label>
          <label className="text-sm text-[var(--text-secondary)]">Repetir a cada minutos (opcional)<input type="number" min={1} value={intervalMinutes} onChange={(e) => setIntervalMinutes(e.target.value)} className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-[var(--text-primary)]" /></label>
        </div>
        <input value={args} onChange={(e) => setArgs(e.target.value)} placeholder='{"query":"status"}' className="mt-3 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 font-mono-data text-sm" />
        {error ? <p className="mt-3 text-sm text-[var(--color-danger)]">{error}</p> : null}
        <button type="button" onClick={() => void createJob()} disabled={!name.trim() || !toolName || !runAt} className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">Agendar</button>
      </section>

      <section className="space-y-3">
        {jobs.length === 0 ? <div className="glass rounded-2xl p-8 text-center text-sm text-[var(--text-secondary)]">Nenhum job agendado.</div> : jobs.map((job) => (
          <article key={job.id} className="glass rounded-2xl p-4">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <h2 className="font-medium">{job.name}</h2>
                <p className="mt-1 font-mono-data text-[10px] text-[var(--text-secondary)]">{job.action_tool} · próxima: {new Date(job.next_run_at).toLocaleString("pt-BR")}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{job.interval_seconds ? `recorrente a cada ${Math.round(job.interval_seconds / 60)} min` : "execução única"}</p>
              </div>
              <button type="button" onClick={() => void setEnabled(job)} className={`p-2 ${job.enabled ? "text-[var(--color-ok)]" : "text-[var(--text-secondary)]"}`} aria-label={job.enabled ? "Pausar" : "Ativar"}><Power className="size-4" /></button>
              <button type="button" onClick={() => void remove(job.id)} className="p-2 text-[var(--color-danger)]" aria-label="Excluir"><Trash2 className="size-4" /></button>
            </div>
          </article>
        ))}
      </section>
    </WorkspaceShell>
  );
}
