"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
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
      const safeNext =
        next.startsWith("/") && !next.startsWith("//") && !next.includes("\\")
          ? next
          : "/";
      router.replace(safeNext);
    } catch {
      setError("Não foi possível conectar ao serviço de identidade.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell flex min-h-dvh items-center justify-center p-5 sm:p-8">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-secondary)] lg:grid-cols-[1fr_1.05fr]">
        <section className="auth-intro hidden flex-col justify-between p-10 lg:flex">
          <div>
            <p className="text-[.75rem] font-bold tracking-[.2em] text-[var(--accent)]">ULTRON</p>
            <h1 className="mt-10 max-w-sm text-4xl font-semibold leading-tight tracking-[-0.04em] text-[var(--text-primary)]">
              Um espaço claro para pensar, decidir e agir.
            </h1>
            <p className="mt-5 max-w-sm text-sm leading-6 text-[var(--text-secondary)]">
              Seu centro de comando pessoal para conversas, memória e ferramentas em um só lugar.
            </p>
          </div>
          <p className="text-xs text-[var(--text-secondary)]">Sessão protegida · Centro de comando</p>
        </section>
        <form onSubmit={submit} className="auth-card space-y-5 p-6 sm:p-10">
        <div>
          <p className="font-mono-data text-[10px] uppercase tracking-[0.3em] text-[var(--accent)]">
            Acesso à sua instância
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">Entrar</h1>
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
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2.5 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
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
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2.5 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
            autoComplete="current-password"
          />
        </label>
        {error ? (
          <p role="alert" aria-live="polite" className="text-sm text-[var(--color-danger)]">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={submitting}
          className="interactive-control w-full rounded-lg bg-[var(--accent)] px-4 py-3 font-semibold text-[#1b1512] hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Validando…" : "Entrar"}
        </button>
        {process.env.NODE_ENV !== "production" ? (
          <p className="text-center text-sm text-[var(--text-secondary)]">
            Primeiro acesso?{" "}
            <Link href="/cadastro" className="text-[var(--accent)] hover:underline">
              Criar conta
            </Link>
          </p>
        ) : (
          <p className="text-center text-xs leading-relaxed text-[var(--text-secondary)]">
            Novos acessos são provisionados pelo administrador da instância.
          </p>
        )}
        </form>
      </div>
    </main>
  );
}
