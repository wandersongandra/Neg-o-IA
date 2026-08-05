"use client";

import type { DashboardData } from "@/lib/types";

interface CoreSphereProps {
  data: DashboardData | null;
}

interface Chip {
  label: string;
  value: string;
  tone?: "ok" | "warn";
}

const BASE_CHIPS: Chip[] = [
  { label: "MODELO ATIVO", value: "GPT-OSS-120B", tone: "ok" },
  { label: "MEMÓRIA UTILIZADA", value: "34%" },
  { label: "NÍVEL DE APRENDIZADO", value: "82%", tone: "ok" },
  { label: "ESTADO COGNITIVO", value: "ESTÁVEL", tone: "ok" },
  { label: "CONFIANÇA", value: "96%", tone: "ok" },
];

const CHIP_POSITIONS = [
  "left-0 top-[12%]",
  "right-0 top-[6%]",
  "left-[-4%] bottom-[22%]",
  "right-[-2%] bottom-[16%]",
  "left-[10%] bottom-[-2%]",
  "right-[8%] top-[38%]",
];

const STATIC_DOTS = [
  { top: "8%", left: "18%", delay: "0s" },
  { top: "16%", left: "78%", delay: "0.8s" },
  { top: "30%", left: "6%", delay: "1.6s" },
  { top: "38%", left: "92%", delay: "0.4s" },
  { top: "55%", left: "3%", delay: "2.1s" },
  { top: "62%", left: "88%", delay: "1.2s" },
  { top: "78%", left: "14%", delay: "2.6s" },
  { top: "84%", left: "70%", delay: "0.2s" },
  { top: "24%", left: "42%", delay: "1.9s" },
  { top: "70%", left: "46%", delay: "1.1s" },
  { top: "12%", left: "58%", delay: "2.4s" },
  { top: "88%", left: "32%", delay: "0.6s" },
];

export default function CoreSphere({ data }: CoreSphereProps) {
  const online = data?.healthz?.status === "alive";
  const latency = data?.latency_ms ?? null;
  const chips: Chip[] = [
    ...BASE_CHIPS.slice(0, 5),
    {
      label: "PROCESSAMENTO",
      value: latency === null ? "--" : `${latency}ms`,
      tone: online ? "ok" : "warn",
    },
  ];

  return (
    <div className="relative mx-auto flex aspect-square w-full max-w-[480px] items-center justify-center">
      <div
        className="animate-glow-pulse absolute size-2/3 rounded-full bg-[#3B82F6]/20 blur-3xl"
        style={{ filter: "blur(60px)" }}
      />

      <div
        className="absolute size-[86%] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 50% 45%, rgba(0,212,255,0.16) 0%, rgba(59,130,246,0.10) 30%, rgba(11,16,24,0) 68%)",
        }}
      />

      <div
        className="animate-spin-slow absolute size-[86%] rounded-full border border-[rgba(0,212,255,0.10)]"
        style={{ borderStyle: "dashed" }}
      />

      <div
        className="animate-spin-reverse absolute size-[64%] rounded-full border-t border-r border-[rgba(0,212,255,0.35)]"
        style={{ transform: "rotateX(70deg)", borderRadius: "999px" }}
      />

      <div className="animate-orbit absolute size-[58%]">
        <span className="absolute -top-1 left-1/2 size-1.5 rounded-full bg-[#00D4FF] shadow-[0_0_10px_#00D4FF]" />
      </div>

      <div className="animate-orbit-reverse absolute size-[74%]">
        <span className="absolute -top-1 left-1/2 size-1 rounded-full bg-[#4DA6FF] shadow-[0_0_10px_#4DA6FF]" />
      </div>

      <div
        className="animate-spin-slow absolute size-[74%] rounded-full"
        style={{
          border: "1px solid transparent",
          borderTopColor: "rgba(0,212,255,0.55)",
          borderRightColor: "rgba(0,212,255,0.15)",
        }}
      />

      <div
        className="relative flex size-[42%] items-center justify-center rounded-full"
        style={{
          background:
            "radial-gradient(circle at 50% 35%, rgba(0,212,255,0.55) 0%, rgba(59,130,246,0.45) 35%, rgba(11,16,24,0.9) 75%)",
          boxShadow:
            "0 0 40px -4px rgba(0,212,255,0.6), 0 0 90px -20px rgba(77,166,255,0.8), inset 0 0 30px rgba(0,212,255,0.35)",
        }}
      >
        <div className="absolute inset-3 rounded-full border border-white/10" />
        <div
          className="absolute inset-0 rounded-full animate-glow-pulse"
          style={{
            background:
              "radial-gradient(circle at 50% 45%, rgba(255,255,255,0.25) 0%, transparent 40%)",
          }}
        />
        <div className="relative text-center leading-none">
          <p className="text-3xl font-black tracking-[0.3em] text-[#F8FAFC] drop-shadow-[0_0_14px_rgba(0,212,255,0.9)]">
            NEGÃO
          </p>
          <p className="mt-2 font-mono-data text-[9px] tracking-[0.45em] text-[#00D4FF]">
            INTELLIGENCE CORE
          </p>
        </div>
      </div>

      {STATIC_DOTS.map((dot, i) => (
        <span
          key={i}
          className="animate-float absolute size-1 rounded-full bg-[#4DA6FF]"
          style={{
            top: dot.top,
            left: dot.left,
            opacity: 0.7,
            boxShadow: "0 0 8px #4DA6FF",
            animationDelay: dot.delay,
          }}
        />
      ))}

      {chips.map((chip, i) => (
        <div
          key={chip.label}
          className={`glass animate-float absolute ${CHIP_POSITIONS[i]}`}
          style={{ animationDelay: `${i * 0.7}s` }}
        >
          <div className="flex items-center gap-2 rounded-lg px-3 py-2">
            <span
              className={`size-1.5 rounded-full ${
                chip.tone === "warn" ? "bg-[#F59E0B]" : "bg-[#22C55E]"
              }`}
              style={{ boxShadow: "0 0 8px currentColor" }}
            />
            <div className="leading-tight">
              <p className="font-mono-data text-[8px] tracking-[0.2em] text-[#94A3B8]">
                {chip.label}
              </p>
              <p className="font-mono-data text-[11px] font-semibold text-[#F8FAFC]">
                {chip.value}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
