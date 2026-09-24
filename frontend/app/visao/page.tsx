"use client";

import { useEffect, useMemo, useState } from "react";
import { Eye, ImagePlus } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface VisionStatus {
  available: boolean;
  model: string | null;
  max_image_bytes: number;
  allowed_mime_types: string[];
  external_processing: boolean;
}

interface VisionResult {
  text: string;
  model: string;
  latency_ms: number;
  mime_type: string;
  bytes_processed: number;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Falha ao ler a imagem."));
    reader.onload = () => {
      const value = String(reader.result ?? "");
      const comma = value.indexOf(",");
      if (comma < 0) {
        reject(new Error("Imagem inválida."));
        return;
      }
      resolve(value.slice(comma + 1));
    };
    reader.readAsDataURL(file);
  });
}

export default function VisionPage() {
  const [status, setStatus] = useState<VisionStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<VisionResult | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void fetch("/api/proxy/vision/status", { cache: "no-store" })
      .then(async (res) => {
        if (res.ok) setStatus((await res.json()) as VisionStatus);
      })
      .catch(() => setMessage("Não foi possível consultar o status da Vision."));
  }, []);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const maxMb = useMemo(
    () => (status ? (status.max_image_bytes / 1024 / 1024).toFixed(1) : "8"),
    [status],
  );

  function chooseFile(next: File | null) {
    setMessage(null);
    setResult(null);
    if (!next) {
      setFile(null);
      return;
    }
    const allowed = status?.allowed_mime_types ?? ["image/png", "image/jpeg", "image/webp"];
    if (!allowed.includes(next.type)) {
      setMessage("Formato não permitido. Use PNG, JPEG ou WebP.");
      return;
    }
    if (status && next.size > status.max_image_bytes) {
      setMessage(`A imagem excede o limite de ${maxMb} MB.`);
      return;
    }
    setFile(next);
  }

  async function analyze() {
    if (!file || !status?.available) return;
    setBusy(true);
    setMessage(null);
    setResult(null);
    try {
      const imageBase64 = await fileToBase64(file);
      const res = await fetch("/api/proxy/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: imageBase64,
          mime_type: file.type,
          prompt: prompt.trim() || undefined,
        }),
      });
      const data = (await res.json()) as VisionResult & { detail?: string };
      if (!res.ok) throw new Error(data.detail ?? "Falha ao analisar imagem");
      setResult(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao analisar imagem");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell
      title="Visão"
      description="Análise multimodal opt-in. A imagem é processada em memória e não é persistida pela Sophie."
    >
      <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <section className="glass rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-[var(--accent)]" />
            <h2 className="font-semibold">Status</h2>
          </div>
          <div className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">
            <p>Disponível: {status?.available ? "sim" : "não"}</p>
            <p>Modelo: {status?.model ?? "não configurado"}</p>
            <p>Limite: {maxMb} MB</p>
            <p>Processamento externo: {status?.external_processing ? "habilitado" : "desabilitado"}</p>
          </div>
          {!status?.available ? (
            <p className="mt-4 rounded-xl border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10 p-3 text-sm text-[var(--color-warn)]">
              Configure EXTERNAL_AI_ENABLED, a chave do provedor e BRAIN_VISION_MODEL para habilitar a análise.
            </p>
          ) : null}
        </section>

        <section className="glass rounded-2xl p-5">
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--accent)]/30 p-6 text-sm text-[var(--accent)]">
            <ImagePlus className="size-5" />
            Selecionar imagem
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
            />
          </label>
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Pré-visualização da imagem selecionada"
              className="mt-4 max-h-80 w-full rounded-xl object-contain"
            />
          ) : null}
        </section>
      </div>

      <section className="glass rounded-2xl p-5">
        <label className="block text-sm font-medium">
          Pergunta ou instrução sobre a imagem
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            maxLength={4000}
            rows={4}
            placeholder="Opcional. Ex.: leia todo o texto visível e explique o que aparece."
            className="mt-2 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm outline-none"
          />
        </label>
        <button
          type="button"
          onClick={() => void analyze()}
          disabled={busy || !file || !status?.available}
          className="mt-3 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
        >
          {busy ? "Analisando..." : "Analisar imagem"}
        </button>
        {message ? <p className="mt-3 text-sm text-[var(--color-warn)]">{message}</p> : null}
      </section>

      {result ? (
        <section className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Resultado</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{result.text}</p>
          <p className="mt-4 font-mono-data text-[10px] text-[var(--text-secondary)]">
            {result.model} · {result.latency_ms}ms · {(result.bytes_processed / 1024).toFixed(1)} KB
          </p>
        </section>
      ) : null}
    </WorkspaceShell>
  );
}
