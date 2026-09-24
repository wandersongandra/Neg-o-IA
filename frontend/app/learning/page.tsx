"use client";

import { useEffect, useState } from "react";
import { Brain, ThumbsDown, ThumbsUp } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface LearningStatus {
  mode: string;
  adaptive_prompt: boolean;
  autonomous_training: boolean;
  storage: string;
}

export default function LearningPage() {
  const [status, setStatus] = useState<LearningStatus | null>(null);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void fetch("/api/proxy/learning/status", { cache: "no-store" }).then(async (res) => {
      if (res.ok) setStatus((await res.json()) as LearningStatus);
    });
  }, []);

  async function submit(rating: -1 | 1) {
    if (!content.trim()) return;
    setBusy(true);
    setSaved(false);
    try {
      const res = await fetch("/api/proxy/learning/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content.trim(), rating }),
      });
      if (res.ok) {
        setContent("");
        setSaved(true);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell title="Aprendizado">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">
          LEARNING V1
        </p>
        <h1 className="mt-2 text-3xl font-semibold">Aprendizado controlado</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          A Sophie registra apenas feedback explícito. Ela não altera sozinha o próprio prompt nem treina modelos.
        </p>
      </header>

      <section className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2">
          <Brain className="size-4 text-[var(--accent)]" />
          <h2 className="font-semibold">Política ativa</h2>
        </div>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div><dt className="text-[var(--text-secondary)]">Modo</dt><dd>{status?.mode ?? "—"}</dd></div>
          <div><dt className="text-[var(--text-secondary)]">Armazenamento</dt><dd>{status?.storage ?? "—"}</dd></div>
          <div><dt className="text-[var(--text-secondary)]">Prompt adaptativo</dt><dd>{status?.adaptive_prompt ? "ativo" : "desativado"}</dd></div>
          <div><dt className="text-[var(--text-secondary)]">Treino autônomo</dt><dd>{status?.autonomous_training ? "ativo" : "desativado"}</dd></div>
        </dl>
      </section>

      <section className="glass rounded-2xl p-5">
        <h2 className="font-semibold">Registrar feedback</h2>
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={5}
          maxLength={2000}
          placeholder="Ex.: prefiro quando você resume primeiro e detalha depois."
          className="mt-4 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" disabled={busy || !content.trim()} onClick={() => void submit(1)} className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-ok)]/30 px-4 py-2 text-sm text-[var(--color-ok)] disabled:opacity-50"><ThumbsUp className="size-4" />Bom comportamento</button>
          <button type="button" disabled={busy || !content.trim()} onClick={() => void submit(-1)} className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-danger)]/30 px-4 py-2 text-sm text-[var(--color-danger)] disabled:opacity-50"><ThumbsDown className="size-4" />Evitar comportamento</button>
        </div>
        {saved ? <p className="mt-3 text-sm text-[var(--color-ok)]">Feedback registrado na memória longa.</p> : null}
      </section>
    </WorkspaceShell>
  );
}
