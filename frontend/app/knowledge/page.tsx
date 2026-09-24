"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Search, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface Doc {
  id: string;
  title: string;
  source_type: string;
  chunk_count: number;
  created_at?: string;
}
interface Hit {
  document_id: string;
  title: string;
  content: string;
  score: number;
}

export default function KnowledgePage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [hits, setHits] = useState<Hit[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch("/api/proxy/knowledge/documents", { cache: "no-store" });
    if (res.ok) {
      const body = (await res.json()) as { documents?: Doc[] };
      setDocs(body.documents ?? []);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function ingest() {
    if (!title.trim() || !content.trim()) return;
    setBusy(true);
    try {
      const res = await fetch("/api/proxy/knowledge/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          content: content.trim(),
          source_type: "manual",
        }),
      });
      if (res.ok) {
        setTitle("");
        setContent("");
        await load();
      }
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (!query.trim()) return;
    const res = await fetch(
      `/api/proxy/knowledge/search?q=${encodeURIComponent(query.trim())}&limit=10`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const body = (await res.json()) as { hits?: Hit[] };
      setHits(body.hits ?? []);
    }
  }

  async function remove(id: string) {
    const res = await fetch(`/api/proxy/knowledge/documents/${id}`, { method: "DELETE" });
    if (res.ok) await load();
  }

  return (
    <WorkspaceShell title="Conhecimento">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">KNOWLEDGE VAULT</p>
        <h1 className="mt-2 text-3xl font-semibold">Base de conhecimento</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Textos são fragmentados, vetorizados e recuperados por relevância semântica.</p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2"><BookOpen className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Adicionar documento</h2></div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={256} placeholder="Título" className="mt-4 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
          <textarea value={content} onChange={(e) => setContent(e.target.value)} maxLength={200000} rows={8} placeholder="Conteúdo..." className="mt-3 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
          <button type="button" onClick={() => void ingest()} disabled={busy || !title.trim() || !content.trim()} className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">Indexar documento</button>
        </div>

        <div className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Documentos indexados</h2>
          <div className="mt-4 space-y-2">
            {docs.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">Nenhum documento indexado.</p> : docs.map((doc) => (
              <div key={doc.id} className="flex items-center gap-3 rounded-xl border border-[var(--border)] p-3">
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{doc.title}</p><p className="font-mono-data text-[10px] text-[var(--text-secondary)]">{doc.source_type} · {doc.chunk_count} chunks</p></div>
                <button type="button" onClick={() => void remove(doc.id)} className="p-2 text-[var(--color-danger)]" aria-label="Excluir documento"><Trash2 className="size-4" /></button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="glass rounded-2xl p-5">
        <div className="flex gap-3">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Pesquisar na base..." className="min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
          <button type="button" onClick={() => void search()} className="inline-flex items-center gap-2 rounded-xl border border-[var(--accent)]/30 px-4 py-2 text-sm text-[var(--accent)]"><Search className="size-4" />Buscar</button>
        </div>
        <div className="mt-4 space-y-2">
          {hits.map((hit, i) => (
            <article key={`${hit.document_id}-${i}`} className="rounded-xl border border-[var(--border)] p-4">
              <div className="flex justify-between gap-3"><h3 className="font-medium">{hit.title}</h3><span className="font-mono-data text-[10px] text-[var(--accent)]">{hit.score.toFixed(2)}</span></div>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{hit.content}</p>
            </article>
          ))}
        </div>
      </section>
    </WorkspaceShell>
  );
}
