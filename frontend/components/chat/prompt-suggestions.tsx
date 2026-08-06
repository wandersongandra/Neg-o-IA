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
    prompt: "Quem é você, NEGÃO? O que você pode fazer por mim?",
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
      <p className="mb-3 text-center font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[#64748B]">
        PODE COMEÇAR POR AQUI
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => onSelect(s.prompt)}
            className="glass glass-hover group flex flex-col items-start gap-2 rounded-xl p-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(0,212,255,0.4)]"
          >
            <s.icon className="size-4 text-[#00D4FF] transition-transform group-hover:scale-110" />
            <span className="text-xs font-medium leading-tight text-[#E2E8F0]">
              {s.title}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
