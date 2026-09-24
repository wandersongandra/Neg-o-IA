"use client";

import { useEffect, useState } from "react";
import { Eye, ImageUp, Loader2 } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface VisionStatus {
  enabled: boolean;
  configured: boolean;
  model: string | null;
  allowed_media_types: string[];
  max_image_bytes: number;
}

export default function VisionPage() {
  const [status, setStatus] = useState<VisionStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/proxy/vision/status", { cache: "no-store" })
      .then(async (res) => res.ok ? setStatus((await res.json()) as VisionStatus) : undefined);
  }, []);

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult("");
    try {
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      for (let offset = 0; offset < bytes.length; offset += 0x8000) {
        binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
      }
      const res = await fetch("/api/proxy/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: btoa(binary),
          media_type: file.type,
          prompt: prompt.trim() || undefined,
        }),
      });
      if (!res.ok) throw new Error();
      const body = (await res.json()) as { text?: string };
      setResult(body.text ?? "");
    } catch {
      setError("Não foi possível analisar a imagem. Verifique se o provider de visão está configurado.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell title="Visão">
      <header>
        <p className="font-mono-data text-[10px] tracking-[0.28em] text-[var(--accent)]">VISION V1</p>
        <h1 className="mt-2 text-3xl font-semibold">Visão da Sophie</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Apenas imagens que você selecionar explicitamente são enviadas ao provider configurado.</p>
      </header>

      <section className="glass rounded-2xl p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2"><Eye className="size-4 text-[var(--accent)]" /><h2 className="font-semibold">Status</h2></div>
          <span className={`font-mono-data text-xs ${status?.configured ? "text-[var(--color-ok)]" : "text-[var(--color-warn)]"}`}>{status?.configured ? "CONFIGURADO" : "INDISPONÍVEL"}</span>
        </div>
        <p className="mt-2 text-xs text-[var(--text-secondary)]">{status?.model ?? "Defina SOPHIE_VISION_ENABLED e SOPHIE_VISION_MODEL no servidor para ativar."}</p>
      </section>

      <section className="glass rounded-2xl p-5">
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-[var(--accent)]/35 p-8 text-sm text-[var(--text-secondary)] hover:bg-[var(--accent-muted)]">
          <ImageUp className="size-5 text-[var(--accent)]" />
          {file ? file.name : "Selecionar PNG, JPEG ou WebP"}
          <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} maxLength={2000} rows={3} placeholder="O que você quer que a Sophie observe?" className="mt-4 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm" />
        <button type="button" onClick={() => void analyze()} disabled={!file || busy || !status?.configured} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" /> : <Eye className="size-4" />}Analisar imagem</button>
        {error ? <p role="alert" className="mt-4 text-sm text-[var(--color-danger)]">{error}</p> : null}
        {result ? <div className="mt-4 rounded-xl border border-[var(--border)] bg-white/[0.02] p-4"><p className="whitespace-pre-wrap text-sm leading-relaxed">{result}</p></div> : null}
      </section>
    </WorkspaceShell>
  );
}
