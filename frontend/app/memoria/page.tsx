"use client";

import { useEffect, useState } from "react";
import { Brain, Search, Save, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface MemoryHit {
  id: string;
  content: string;
  source: string;
  importance: number;
  score: number;
  created_at: string;
}

interface MemoryPolicy {
  auto_capture_enabled: boolean;
  retention_days: number;
}

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [content, setContent] = useState("");
  const [hits, setHits] = useState<MemoryHit[]>([]);
  const [policy, setPolicy] = useState<MemoryPolicy>({
    auto_capture_enabled: false,
    retention_days: 90,
  });
  const [status, setStatus] = useState<string>("carregando");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      fetch("/api/proxy/memory/status", { cache: "no-store" }),
      fetch("/api/proxy/memory/policy", { cache: "no-store" }),
    ]).then(async ([statusRes, policyRes]) => {
      if (statusRes.ok) {
        const data = (await statusRes.json()) as { long_term?: string };
        setStatus(data.long_term ?? "disponível");
      } else {
        setStatus("indisponível");
      }
      if (policyRes.ok) {
        setPolicy((await policyRes.json()) as MemoryPolicy);
      }
    }).catch(() => setStatus("indisponível"));
  }, []);

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: "10" });
      const res = await fetch(`/api/proxy/memory/search?${params}`, { cache: "no-store" });
      if (!res.ok) throw new Error("Falha ao buscar memória");
      const data = (await res.json()) as { hits?: MemoryHit[] };
      setHits(data.hits ?? []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao buscar");
    } finally {
      setBusy(false);
    }
  }

  async function remember() {
    const value = content.trim();
    if (!value) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch("/api/proxy/memory/long-term", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: value, importance: 0.7 }),
      });
      if (!res.ok) throw new Error("Falha ao salvar memória");
      setContent("");
      setMessage("Memória salva.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setBusy(false);
    }
  }

  async function remove(memoryId: string) {
    if (!window.confirm("Excluir esta memória?")) return;
    const res = await fetch(`/api/proxy/memory/long-term/${memoryId}`, {
      method: "DELETE",
    });
    if (res.ok) setHits((current) => current.filter((item) => item.id !== memoryId));
  }

  async function updatePolicy(next: MemoryPolicy) {
    setPolicy(next);
    const res = await fetch("/api/proxy/memory/policy", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(next),
    });
    if (!res.ok) setMessage("Não foi possível atualizar a política de memória.");
  }

  return (
    <WorkspaceShell
      title="Memória"
      description="Memória pessoal persistente em PostgreSQL + pgvector, isolada por usuário."
    >
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="glass rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2">
            <Brain className="size-4 text-[var(--accent)]" />
            <h2 className="font-semibold">Guardar informação</h2>
          </div>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            maxLength={4000}
            rows={6}
            placeholder="Ex.: Prefiro respostas curtas e objetivas."
            className="w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none"
          />
          <button
            type="button"
            disabled={busy || !content.trim()}
            onClick={() => void remember()}
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
          >
            <Save className="size-4" />
            Salvar memória
          </button>
        </section>

        <section className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Política de retenção</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Backend: {status}</p>
          <label className="mt-4 flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              checked={policy.auto_capture_enabled}
              onChange={(event) =>
                void updatePolicy({ ...policy, auto_capture_enabled: event.target.checked })
              }
            />
            Capturar automaticamente mensagens úteis
          </label>
          <label className="mt-4 block text-sm text-[var(--text-secondary)]">
            Retenção automática em dias
            <input
              type="number"
              min={1}
              max={3650}
              value={policy.retention_days}
              onChange={(event) =>
                setPolicy({ ...policy, retention_days: Number(event.target.value) })
              }
              onBlur={() => void updatePolicy(policy)}
              className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-[var(--text-primary)]"
            />
          </label>
        </section>
      </div>

      <section className="glass rounded-2xl p-5">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void search();
            }}
            placeholder="Buscar semanticamente nas memórias..."
            className="min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm outline-none"
          />
          <button
            type="button"
            onClick={() => void search()}
            disabled={busy || !query.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--accent)]/30 px-4 py-2.5 text-sm text-[var(--accent)] disabled:opacity-50"
          >
            <Search className="size-4" />
            Buscar
          </button>
        </div>
        {message ? <p className="mt-3 text-sm text-[var(--text-secondary)]">{message}</p> : null}
        <div className="mt-4 space-y-3">
          {hits.map((hit) => (
            <article key={hit.id} className="rounded-xl border border-[var(--border)] p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm leading-relaxed">{hit.content}</p>
                <button
                  type="button"
                  onClick={() => void remove(hit.id)}
                  className="text-[var(--color-danger)]"
                  aria-label="Excluir memória"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
              <p className="mt-2 font-mono-data text-[10px] text-[var(--text-secondary)]">
                {hit.source} · relevância {(hit.score * 100).toFixed(0)}%
              </p>
            </article>
          ))}
          {!busy && hits.length === 0 ? (
            <p className="text-sm text-[var(--text-secondary)]">Nenhum resultado carregado.</p>
          ) : null}
        </div>
      </section>
    </WorkspaceShell>
  );
}
