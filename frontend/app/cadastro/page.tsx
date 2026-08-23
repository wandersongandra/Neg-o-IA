"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function CadastroPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < 12) {
      setError("A senha precisa ter pelo menos 12 caracteres.");
      return;
    }
    if (password !== confirmation) {
      setError("As senhas não coincidem.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          display_name: displayName.trim() || undefined,
        }),
      });
      if (!response.ok) {
        setError(response.status === 409 ? "Esse usuário já existe." : "Não foi possível criar a conta.");
        return;
      }
      router.replace("/login?registered=1");
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
            SOPHIE CORE — BOOTSTRAP
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">Criar acesso</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Crie o único usuário inicial da sua instância.
          </p>
        </div>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Usuário
          <input required minLength={3} maxLength={128} value={username} onChange={(event) => setUsername(event.target.value)} className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" autoComplete="username" />
        </label>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Nome de exibição <span className="opacity-60">(opcional)</span>
          <input maxLength={256} value={displayName} onChange={(event) => setDisplayName(event.target.value)} className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" autoComplete="name" />
        </label>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Senha
          <input required minLength={12} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" autoComplete="new-password" />
        </label>
        <label className="block space-y-2 text-sm text-[var(--text-secondary)]">
          Confirmar senha
          <input required minLength={12} type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3 py-2 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" autoComplete="new-password" />
        </label>
        {error ? <p className="text-sm text-[var(--color-danger)]">{error}</p> : null}
        <button type="submit" disabled={submitting} className="w-full rounded-xl bg-[var(--accent)] px-4 py-2.5 font-semibold text-black disabled:opacity-50">
          {submitting ? "Criando…" : "Criar conta"}
        </button>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Já possui acesso?{" "}
          <Link href="/login" className="text-[var(--accent)] hover:underline">Entrar</Link>
        </p>
      </form>
    </main>
  );
}
