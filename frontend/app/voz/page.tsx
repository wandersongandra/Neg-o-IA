import type { Metadata } from "next";
import Link from "next/link";
import VoicePanel from "@/components/voice/voice-panel";

export const metadata: Metadata = {
  title: "Voz — NEGÃO AI",
  description: "Fale com o NEGÃO e ouça as respostas dele em voz alta.",
};

export default function VozPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col p-5 md:p-6">
      <header className="animate-fade-in mb-6">
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:text-[var(--accent)]"
        >
          ← Voltar ao painel
        </Link>
        <p className="font-mono-data text-[10px] font-semibold tracking-[0.3em] text-[var(--accent)]">
          NEGÃO AI // INTERFACE DE VOZ
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Fale com o <span className="glow-text text-gradient">NEGÃO</span>
        </h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Grave sua pergunta para transcrição ou faça o NEGÃO falar um texto em
          voz alta.
        </p>
      </header>
      <VoicePanel />
    </main>
  );
}
