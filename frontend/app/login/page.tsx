"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        setError(response.status === 503 ? "Identidade indisponível." : "Credenciais inválidas.");
        return;
      }
      const next = new URLSearchParams(window.location.search).get("next") || "/";
      router.replace(next.startsWith("/") ? next : "/");
    } catch {
      setError("Não foi possível conectar ao serviço de identidade.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-[var(--bg)] p-6">
      <form onSubmit={submit} className="glass w-full max-w-md space-y-5 rounded-2xl p-6">
        <div>
          <p className="font-mono-data text-[10px] uppercase tracking-[0.3em] text-[var(--accent)]">
            SOPHIE CORE — IDENTITY
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">Entrar</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Use uma sessão autenticada para acessar suas conversas.
          </p>
        </div>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Usuário
          <input
            required
            minLength={3}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
            autoComplete="username"
          />
        </label>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Senha
          <input
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
            autoComplete="current-password"
          />
        </label>
        {error ? <p className="text-sm text-[var(--color-danger)]">{error}</p> : null}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-[var(--accent)] px-4 py-2.5 font-semibold text-black disabled:opacity-50"
        >
          {submitting ? "Validando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
