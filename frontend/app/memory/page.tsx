"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Search, Save, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface MemoryItem {
  id: string;
  content: string;
  source: string;
  importance: number;
  created_at: string;
  expires_at: string | null;
}

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [autoCapture, setAutoCapture] = useState(false);
  const [retentionDays, setRetentionDays] = useState(90);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [memRes, policyRes] = await Promise.all([
      fetch("/api/proxy/memory/long-term?limit=50", { cache: "no-store" }),
      fetch("/api/proxy/memory/policy", { cache: "no-store" }),
    ]);
    if (memRes.ok) {
      const body = (await memRes.json()) as { memories?: MemoryItem[] };
      setItems(body.memories ?? []);
    }
    if (policyRes.ok) {
      const policy = (await policyRes.json()) as {
        auto_capture_enabled?: boolean;
        retention_days?: number;
      };
      setAutoCapture(Boolean(policy.auto_capture_enabled));
      setRetentionDays(policy.retention_days ?? 90);
    }
  }, []);

  useEffect(() => {
    void load().catch(() => setError("Não foi possível carregar a memória."));
  }, [load]);

  async function remember() {
    if (!draft.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/memory/long-term", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: draft.trim(), importance: 0.7 }),
      });
      if (!res.ok) throw new Error();
      setDraft("");
      await load();
    } catch {
      setError("Não foi possível salvar a memória.");
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (!query.trim()) {
      await load();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/proxy/memory/search?q=${encodeURIComponent(query.trim())}&limit=10`,
        { cache: "no-store" },
      );
      if (!res.ok) throw new Error();
      const body = (await res.json()) as {
        hits?: Array<{ id: string; content: string; source: string; importance: number; created_at: string }>;
      };
      setItems(
        (body.hits ?? []).map((hit) => ({
          ...hit,
          expires_at: null,
        })),
      );
    } catch {
      setError("A busca de memória falhou.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    const res = await fetch(`/api/proxy/memory/long-term/${id}`, { method: "DELETE" });
    if (res.ok) setItems((current) => current.filter((item) => item.id !== id));
  }

  async function savePolicy() {
    setBusy(true);
    try {
      await fetch("/api/proxy/memory/policy", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auto_capture_enabled: autoCapture,
          retention_days: retentionDays,
        }),
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell title="Memória">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">LONG-TERM MEMORY</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Memória da Sophie</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Memórias persistidas no PostgreSQL/pgvector, isoladas pela sua identidade.
        </p>
      </header>

      {error ? <p role="alert" className="glass rounded-xl p-3 text-sm text-[var(--color-danger)]">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2"><Brain className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Guardar memória</h2></div>
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={4000} rows={5} placeholder="Ex.: prefiro respostas curtas e objetivas" className="mt-4 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none" />
          <button type="button" onClick={() => void remember()} disabled={busy || !draft.trim()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"><Save className="size-4" />Salvar</button>
        </div>

        <div className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Política de retenção</h2>
          <label className="mt-4 flex items-center gap-3 text-sm">
            <input type="checkbox" checked={autoCapture} onChange={(e) => setAutoCapture(e.target.checked)} />
            Captura automática de mensagens relevantes
          </label>
          <label className="mt-4 block text-sm text-[var(--text-secondary)]">
            Retenção (dias)
            <input type="number" min={1} max={3650} value={retentionDays} onChange={(e) => setRetentionDays(Number(e.target.value))} className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-[var(--text-primary)]" />
          </label>
          <button type="button" onClick={() => void savePolicy()} disabled={busy} className="mt-3 rounded-xl border border-[var(--accent)]/30 px-4 py-2 text-sm text-[var(--accent)] disabled:opacity-50">Aplicar política</button>
        </div>
      </section>

      <section className="glass rounded-2xl p-5">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar semanticamente na memória..." className="min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none" />
          <button type="button" onClick={() => void search()} disabled={busy} className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--accent)]/30 px-4 py-2 text-sm text-[var(--accent)]"><Search className="size-4" />Buscar</button>
        </div>
        <div className="mt-4 space-y-2">
          {items.length === 0 ? <p className="py-6 text-center text-sm text-[var(--text-secondary)]">Nenhuma memória encontrada.</p> : items.map((item) => (
            <article key={item.id} className="rounded-xl border border-[var(--border)] bg-white/[0.02] p-4">
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="whitespace-pre-wrap text-sm text-[var(--text-primary)]">{item.content}</p>
                  <p className="mt-2 font-mono-data text-[10px] text-[var(--text-secondary)]">{item.source} · importância {item.importance.toFixed(2)} · {new Date(item.created_at).toLocaleString("pt-BR")}</p>
                </div>
                <button type="button" onClick={() => void remove(item.id)} className="rounded-lg p-2 text-[var(--color-danger)]" aria-label="Excluir memória"><Trash2 className="size-4" /></button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </WorkspaceShell>
  );
}
