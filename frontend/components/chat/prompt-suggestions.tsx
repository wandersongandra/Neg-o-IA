"use client";

import { Bot, Brain, Code2, Rocket, Search, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Suggestion {
  icon: LucideIcon;
  title: string;
  prompt: string;
}

const SUGGESTIONS: Suggestion[] = [
  {
    icon: Bot,
    title: "Apresente-se",
    prompt: "Quem é você, Sophie? O que você pode fazer por mim?",
  },
  {
    icon: Brain,
    title: "Estado do sistema",
    prompt: "Qual é o estado atual do sistema? Verifique todos os módulos.",
  },
  {
    icon: Code2,
    title: "Escrever código",
    prompt: "Escreva um script em Python que liste arquivos de um diretório.",
  },
  {
    icon: ShieldCheck,
    title: "Segurança",
    prompt: "Quais são as boas práticas de segurança para uma API?",
  },
  {
    icon: Search,
    title: "Investigar",
    prompt: "Investigue por que um serviço pode estar lento e como diagnosticar.",
  },
  {
    icon: Rocket,
    title: "Produtividade",
    prompt: "Monte um plano de tarefas para priorizar meu dia de trabalho.",
  },
];

export default function PromptSuggestions({
  onSelect,
}: {
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="w-full max-w-xl">
      <p className="mb-3 text-center font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[var(--text-secondary)]">
        PODE COMEÇAR POR AQUI
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => onSelect(s.prompt)}
            className="glass glass-hover group flex flex-col items-start gap-2 rounded-xl p-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_var(--accent-glow)]"
          >
            <s.icon className="size-4 text-[var(--accent)] transition-transform group-hover:scale-110" />
            <span className="text-xs font-medium leading-tight text-[var(--text-primary)]">
              {s.title}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
