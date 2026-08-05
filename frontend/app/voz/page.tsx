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
          className="mb-4 inline-flex items-center gap-1.5 text-xs text-[#64748B] transition-colors hover:text-[#00D4FF]"
        >
          ← Voltar ao painel
        </Link>
        <p className="font-mono-data text-[10px] font-semibold tracking-[0.3em] text-[#00D4FF]">
          NEGÃO AI // INTERFACE DE VOZ
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#F8FAFC]">
          Fale com o <span className="glow-text text-gradient">NEGÃO</span>
        </h1>
        <p className="mt-1 text-sm text-[#94A3B8]">
          Grave sua pergunta para transcrição ou faça o NEGÃO falar um texto em
          voz alta.
        </p>
      </header>
      <VoicePanel />
    </main>
  );
}
