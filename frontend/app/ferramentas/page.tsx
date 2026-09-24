"use client";

import { useEffect, useMemo, useState } from "react";
import { Play, ShieldCheck } from "lucide-react";
import WorkspaceShell from "@/components/workspace-shell";

interface ToolSpec {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  risk: string;
  requires_confirmation: boolean;
  automation_safe: boolean;
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [selectedName, setSelectedName] = useState("");
  const [argumentsText, setArgumentsText] = useState("{}");
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void fetch("/api/proxy/tool-manager/catalog", { cache: "no-store" })
      .then(async (res) => {
        if (!res.ok) return;
        const data = (await res.json()) as { tools?: ToolSpec[] };
        const catalog = data.tools ?? [];
        setTools(catalog);
        if (catalog[0]) setSelectedName(catalog[0].name);
      })
      .catch(() => setMessage("Não foi possível carregar o catálogo."));
  }, []);

  const selected = useMemo(
    () => tools.find((tool) => tool.name === selectedName) ?? null,
    [tools, selectedName],
  );

  async function execute() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    setResult(null);
    try {
      const parsed = JSON.parse(argumentsText) as unknown;
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("Os argumentos precisam ser um objeto JSON.");
      }
      const res = await fetch("/api/proxy/tool-manager/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: selected.name,
          arguments: parsed,
          confirmed,
          idempotency_key: `ui-${selected.name}-${Date.now()}`,
        }),
      });
      const data = (await res.json()) as Record<string, unknown>;
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Falha ao executar ferramenta",
        );
      }
      setResult(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao executar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell
      title="Ferramentas"
      description="Tool Manager fechado: somente capacidades registradas podem ser executadas."
    >
      <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <section className="glass rounded-2xl p-5">
          <h2 className="font-semibold">Catálogo permitido</h2>
          <div className="mt-4 space-y-2">
            {tools.map((tool) => (
              <button
                key={tool.name}
                type="button"
                onClick={() => {
                  setSelectedName(tool.name);
                  setConfirmed(false);
                  setArgumentsText("{}");
                  setResult(null);
                }}
                className={`w-full rounded-xl border p-3 text-left transition-colors ${
                  selectedName === tool.name
                    ? "border-[var(--accent)]/40 bg-[var(--accent-muted)]"
                    : "border-[var(--border)]"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono-data text-xs text-[var(--accent)]">
                    {tool.name}
                  </span>
                  <span className="text-[10px] uppercase text-[var(--text-secondary)]">
                    {tool.risk}
                  </span>
                </div>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{tool.description}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="glass rounded-2xl p-5">
          {selected ? (
            <>
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-[var(--accent)]" />
                <h2 className="font-semibold">{selected.name}</h2>
              </div>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{selected.description}</p>
              <p className="mt-3 font-mono-data text-[10px] text-[var(--text-secondary)]">
                schema: {JSON.stringify(selected.input_schema)}
              </p>
              <label className="mt-4 block text-sm">
                Argumentos JSON
                <textarea
                  value={argumentsText}
                  onChange={(event) => setArgumentsText(event.target.value)}
                  rows={9}
                  spellCheck={false}
                  className="mt-2 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 font-mono-data text-xs outline-none"
                />
              </label>
              {selected.requires_confirmation ? (
                <label className="mt-3 flex items-center gap-2 text-sm text-[var(--color-warn)]">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)}
                  />
                  Confirmo explicitamente esta ação de escrita
                </label>
              ) : null}
              <button
                type="button"
                onClick={() => void execute()}
                disabled={
                  busy || (selected.requires_confirmation && !confirmed)
                }
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                <Play className="size-4" />
                Executar
              </button>
            </>
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">Carregando ferramentas...</p>
          )}
          {message ? <p className="mt-4 text-sm text-[var(--color-warn)]">{message}</p> : null}
          {result ? (
            <pre className="mt-4 max-h-96 overflow-auto rounded-xl bg-black/20 p-3 font-mono-data text-xs text-[var(--text-secondary)]">
              {JSON.stringify(result, null, 2)}
            </pre>
          ) : null}
        </section>
      </div>
    </WorkspaceShell>
  );
}
