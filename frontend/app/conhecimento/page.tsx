"use client";

import { useEffect, useState } from "react";
import { FilePlus2, Search, Trash2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface KnowledgeDocument {
  id: string;
  title: string;
  source_type: string;
  chunk_count: number;
  created_at: string;
}

interface KnowledgeHit {
  document_id: string;
  chunk_id: string;
  title: string;
  content: string;
  score: number;
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<KnowledgeHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function loadDocuments() {
    const res = await fetch("/api/proxy/knowledge/documents", { cache: "no-store" });
    if (!res.ok) return;
    const data = (await res.json()) as { documents?: KnowledgeDocument[] };
    setDocuments(data.documents ?? []);
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function ingest() {
    if (!title.trim() || !content.trim()) return;
    setBusy(true);
    setMessage(null);
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
      if (!res.ok) throw new Error("Falha ao adicionar documento");
      setTitle("");
      setContent("");
      setMessage("Documento indexado.");
      await loadDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao indexar");
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: "10" });
      const res = await fetch(`/api/proxy/knowledge/search?${params}`, { cache: "no-store" });
      if (!res.ok) throw new Error("Falha ao pesquisar");
      const data = (await res.json()) as { hits?: KnowledgeHit[] };
      setHits(data.hits ?? []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao pesquisar");
    } finally {
      setBusy(false);
    }
  }

  async function remove(documentId: string) {
    if (!window.confirm("Excluir este documento e todos os seus chunks?")) return;
    const res = await fetch(`/api/proxy/knowledge/documents/${documentId}`, {
      method: "DELETE",
    });
    if (res.ok) {
      setDocuments((current) => current.filter((doc) => doc.id !== documentId));
      setHits((current) => current.filter((hit) => hit.document_id !== documentId));
    }
  }

  return (
    <WorkspaceShell
      title="Conhecimento"
      description="Knowledge Vault com chunking, embeddings e recuperação semântica por usuário."
    >
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="glass rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2">
            <FilePlus2 className="size-4 text-[var(--accent)]" />
            <h2 className="font-semibold">Adicionar conhecimento</h2>
          </div>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={256}
            placeholder="Título"
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-sm outline-none"
          />
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            maxLength={200000}
            rows={9}
            placeholder="Cole aqui documentação, notas ou conhecimento que a Sophie deve consultar."
            className="mt-3 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none"
          />
          <button
            type="button"
            onClick={() => void ingest()}
            disabled={busy || !title.trim() || !content.trim()}
            className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
          >
            Indexar documento
          </button>
        </section>

        <section className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Documentos indexados</h2>
          <div className="mt-4 space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{doc.title}</p>
                  <p className="font-mono-data text-[10px] text-[var(--text-secondary)]">
                    {doc.chunk_count} chunks · {doc.source_type}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void remove(doc.id)}
                  className="text-[var(--color-danger)]"
                  aria-label={`Excluir ${doc.title}`}
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
            {documents.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">Nenhum documento indexado.</p>
            ) : null}
          </div>
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
            placeholder="Pesquisar na base de conhecimento..."
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
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {hits.map((hit) => (
            <article key={hit.chunk_id} className="rounded-xl border border-[var(--border)] p-4">
              <p className="font-medium">{hit.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{hit.content}</p>
              <p className="mt-2 font-mono-data text-[10px] text-[var(--accent)]">
                relevância {(hit.score * 100).toFixed(0)}%
              </p>
            </article>
          ))}
        </div>
      </section>
    </WorkspaceShell>
  );
}
