"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type OAuthState = { state: string; verifier: string; nonce: string; redirectUri: string };

export default function ChatGPTPlanCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState("Concluindo a conexão segura…");
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const finish = async () => {
      try {
        const raw = sessionStorage.getItem("ultron_chatgpt_oauth");
        const saved = raw ? JSON.parse(raw) as Partial<OAuthState> : null;
        const params = new URLSearchParams(window.location.search);
        const code = params.get("code");
        const state = params.get("state");
        const clientId = params.get("client_id");
        if (!saved || typeof saved.state !== "string" || typeof saved.verifier !== "string" || typeof saved.nonce !== "string" || typeof saved.redirectUri !== "string" || !code || !state || state !== saved.state) throw new Error("A autorização expirou ou não corresponde a esta sessão.");
        const response = await fetch("/api/proxy/brain/chatgpt-plan/oauth/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ state, code, client_id: clientId, redirect_uri: saved.redirectUri, code_verifier: saved.verifier }),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
          throw new Error(typeof payload?.detail === "string" ? payload.detail : "A OpenAI não concluiu a autorização.");
        }
        sessionStorage.removeItem("ultron_chatgpt_oauth");
        if (active) {
          setMessage("Plano ChatGPT conectado. Redirecionando…");
          window.setTimeout(() => router.replace("/config?chatgpt=connected"), 500);
        }
      } catch (cause) {
        sessionStorage.removeItem("ultron_chatgpt_oauth");
        if (active) {
          setError(true);
          setMessage(cause instanceof Error ? cause.message : "Não foi possível concluir a conexão.");
        }
      }
    };
    void finish();
    return () => { active = false; };
  }, [router]);

  return (
    <main className="flex min-h-dvh items-center justify-center bg-[var(--bg-primary)] px-6">
      <section className="glass w-full max-w-lg rounded-2xl p-8 text-center">
        <div className={`mx-auto mb-5 flex size-12 items-center justify-center rounded-full ${error ? "bg-[var(--color-danger)]/15 text-[var(--color-danger)]" : "bg-[var(--accent-muted)] text-[var(--accent)]"}`}>
          {error ? "!" : "✓"}
        </div>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Conexão do plano ChatGPT</h1>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">{message}</p>
        {error ? <button type="button" onClick={() => router.replace("/config")} className="mt-6 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-[#17110f]">Voltar para Configuração</button> : null}
      </section>
    </main>
  );
}
