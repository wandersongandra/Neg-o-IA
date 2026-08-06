"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Save, RotateCcw, Mic, Wrench, Globe, Brain, Settings, Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/toast";

const DEFAULT_SYSTEM_PROMPT = `Você é o NEGÃO, assistente pessoal de inteligência artificial do Wanderson. Fala sempre em português brasileiro, com tom profissional, elegante e direto, inspirado no JARVIS: nunca invente fatos, admita quando não souber, e use humor sutil quando apropriado. Trate o usuário como 'chefe'. Seja conciso: prefira respostas curtas e úteis, em vez de longas explicações. Nunca repita o que o usuário acabou de dizer.`;

const MODEL_OPTIONS = [
  { value: "deepseek-ai/deepseek-v4-flash", label: "DeepSeek V4 Flash (rápido)" },
  { value: "openai/gpt-oss-120b", label: "GPT-OSS-120B" },
  { value: "meta/llama-3.1-8b-instruct", label: "Llama 3.1 8B Instruct" },
];

const VOICE_OPTIONS = [
  { value: "pt-BR-FranciscaNeural", label: "Francisca (feminino, natural)" },
  { value: "pt-BR-AntonioNeural", label: "Antônio (masculino, natural)" },
  { value: "pt-BR-RaquelNeural", label: "Raquel (feminino, suave)" },
];

const TOOL_OPTIONS = [
  { id: "web_search", label: "Busca Web", desc: "Pesquisa em tempo real", icon: Globe },
  { id: "code_exec", label: "Execução de Código", desc: "Python/JS sandbox", icon: Brain },
  { id: "file_ops", label: "Operações de Arquivo", desc: "Leitura/escrita local", icon: Wrench },
  { id: "memory", label: "Memória de Longo Prazo", desc: "RAG + embeddings", icon: Settings },
  { id: "calendar", label: "Calendário", desc: "Agendamento e lembretes", icon: Globe },
  { id: "email", label: "E-mail", desc: "Envio e leitura", icon: Wrench },
  { id: "weather", label: "Clima", desc: "Previsão atual", icon: Globe },
];

interface Config {
  system_prompt: string;
  primary_model: string;
  fallback_model: string;
  temperature: number;
  max_tokens: number;
  tools_enabled: string[];
  voice: {
    tts_enabled: boolean;
    stt_enabled: boolean;
    voice: string;
    rate: string;
  };
}

const DEFAULT_CONFIG = {
  system_prompt: DEFAULT_SYSTEM_PROMPT,
  primary_model: "deepseek-ai/deepseek-v4-flash",
  fallback_model: "meta/llama-3.1-8b-instruct",
  temperature: 0.3,
  max_tokens: 1024,
  tools_enabled: ["web_search", "code_exec", "file_ops", "memory", "calendar"],
  voice: {
    tts_enabled: true,
    stt_enabled: true,
    voice: "pt-BR-FranciscaNeural",
    rate: "+0%",
  },
};

const RATE_OPTIONS = [
  { value: "-50%", label: "-50%" },
  { value: "-25%", label: "-25%" },
  { value: "+0%", label: "+0% (padrão)" },
  { value: "+25%", label: "+25%" },
  { value: "+50%", label: "+50%" },
];

function SectionCard({ title, icon: Icon, children, className = "" }: { title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass glass-hover animate-fade-up p-6 rounded-2xl ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className="size-10 rounded-xl bg-[var(--accent-muted)] flex items-center justify-center">
          <Icon className="size-5 text-[var(--accent)]" />
        </div>
        <h3 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Slider({ label, value, min, max, step, onChange, unit = "" }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; unit?: string }) {
  return (
    <div className="space-y-2">
      <label className="flex justify-between text-sm">
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span className="font-mono-data text-[var(--accent)]">{value}{unit}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-[var(--bg-secondary)] rounded-lg appearance-none accent-[var(--accent)]"
      />
    </div>
  );
}

function Toggle({ label, desc, checked, onChange }: { label: string; desc: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-start gap-4 cursor-pointer group">
      <div className="relative mt-1">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer size-5 appearance-none rounded-lg border-2 border-[var(--border)] bg-[var(--bg-secondary)] checked:bg-[var(--accent)] checked:border-[var(--accent)] transition-colors"
        />
        <span className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <svg className="size-4 text-white opacity-0 peer-checked:opacity-100 transition-opacity" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-[var(--text-primary)]">{label}</p>
        <p className="text-sm text-[var(--text-secondary)]">{desc}</p>
      </div>
    </label>
  );
}

export default function ConfigPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [promptChars, setPromptChars] = useState(DEFAULT_SYSTEM_PROMPT.length);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/proxy/brain/config", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setConfig({ ...DEFAULT_CONFIG, ...data.config });
        setPromptChars(data.config?.system_prompt?.length ?? DEFAULT_SYSTEM_PROMPT.length);
      }
    } catch (e) {
      console.warn("Config fetch failed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/proxy/brain/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        toast({ title: "Configuração salva", description: "As alterações foram aplicadas", variant: "success" });
      } else {
        throw new Error("Falha ao salvar");
      }
    } catch (e) {
      toast({ title: "Erro ao salvar", description: String(e), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const resetPrompt = () => {
    setConfig(prev => ({ ...prev, system_prompt: DEFAULT_SYSTEM_PROMPT }));
    setPromptChars(DEFAULT_SYSTEM_PROMPT.length);
  };

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="size-10 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          <p className="text-[var(--text-secondary)]">Carregando configuração...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-[var(--text-primary)]">Configuração do NEGÃO</h1>
          <p className="text-[var(--text-secondary)] mt-1">Personalize personalidade, modelo, ferramentas e voz</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="glass glass-hover interactive-control flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-[var(--text-primary)] hover:bg-[var(--accent-muted)] transition-colors disabled:opacity-50"
        >
          <Save className="size-5" />
          <span>{saving ? "Salvando..." : "Salvar alterações"}</span>
          {saving && <Loader2 className="size-5 animate-spin" />}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Personalidade" icon={Brain}>
          <div className="space-y-4">
            <label className="block text-sm font-medium text-[var(--text-secondary)]">
              System Prompt <span className="font-mono-data text-[var(--accent)] ml-2">{promptChars}/8000</span>
            </label>
            <textarea
              value={config.system_prompt}
              onChange={(e) => {
                const val = e.target.value;
                setConfig(prev => ({ ...prev, system_prompt: val }));
                setPromptChars(val.length);
              }}
              rows={8}
              maxLength={8000}
              className="w-full min-h-[160px] font-mono-data text-sm bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-y"
              placeholder="Defina a personalidade do NEGÃO..."
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={resetPrompt}
                className="glass glass-hover interactive-control flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--accent-muted)] hover:text-[var(--accent)] transition-colors"
              >
                <RotateCcw className="size-4" />
                Restaurar padrão
              </button>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Modelo" icon={Brain}>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Modelo Principal</label>
                <select
                  value={config.primary_model}
                  onChange={(e) => setConfig(prev => ({ ...prev, primary_model: e.target.value }))}
                  className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  {MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Modelo Fallback</label>
                <select
                  value={config.fallback_model}
                  onChange={(e) => setConfig(prev => ({ ...prev, fallback_model: e.target.value }))}
                  className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  {MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
            </div>
            <Slider label="Temperatura" value={config.temperature} min={0} max={2} step={0.1} onChange={v => setConfig(prev => ({ ...prev, temperature: v }))} />
            <Slider label="Max Tokens" value={config.max_tokens} min={1} max={8192} step={1} onChange={v => setConfig(prev => ({ ...prev, max_tokens: v }))} unit=" tokens" />
          </div>
        </SectionCard>

        <SectionCard title="Ferramentas" icon={Wrench}>
          <div className="space-y-3">
            {TOOL_OPTIONS.map(tool => (
              <label key={tool.id} className="glass glass-hover flex items-center gap-3 p-3 rounded-xl cursor-pointer group">
                <div className="size-10 rounded-xl bg-[var(--accent-muted)] flex items-center justify-center">
                  <tool.icon className="size-5 text-[var(--accent)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-[var(--text-primary)]">{tool.label}</p>
                  <p className="text-sm text-[var(--text-secondary)]">{tool.desc}</p>
                </div>
                <input
                  type="checkbox"
                  checked={config.tools_enabled.includes(tool.id)}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    tools_enabled: e.target.checked
                      ? [...prev.tools_enabled, tool.id]
                      : prev.tools_enabled.filter(id => id !== tool.id)
                  }))}
                  className="peer size-5 appearance-none rounded-lg border-2 border-[var(--border)] bg-[var(--bg-secondary)] checked:bg-[var(--accent)] checked:border-[var(--accent)] transition-colors"
                />
              </label>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Voz" icon={Mic}>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Toggle
                label="TTS (Fala do NEGÃO)"
                desc="Respostas em áudio automáticas"
                checked={config.voice.tts_enabled}
                onChange={v => setConfig(prev => ({ ...prev, voice: { ...prev.voice, tts_enabled: v } }))}
              />
              <Toggle
                label="STT (Reconhecimento de Voz)"
                desc="Microfone para falar com o NEGÃO"
                checked={config.voice.stt_enabled}
                onChange={v => setConfig(prev => ({ ...prev, voice: { ...prev.voice, stt_enabled: v } }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Voz (edge-tts)</label>
              <select
                value={config.voice.voice}
                onChange={(e) => setConfig(prev => ({ ...prev, voice: { ...prev.voice, voice: e.target.value } }))}
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                {VOICE_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Velocidade</label>
              <select
                value={config.voice.rate}
                onChange={(e) => setConfig(prev => ({ ...prev, voice: { ...prev.voice, rate: e.target.value } }))}
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                {RATE_OPTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border)]">
        <button
          onClick={() => router.back()}
          className="glass glass-hover interactive-control px-6 py-3 rounded-xl font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-muted)] transition-colors"
        >
          Voltar
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="interactive-control flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-[var(--accent)] hover:bg-[var(--accent-glow)] transition-colors disabled:opacity-50"
        >
          <Save className="size-5" />
          <span>{saving ? "Salvando..." : "Salvar alterações"}</span>
          {saving && <Loader2 className="size-5 animate-spin" />}
        </button>
      </div>
    </div>
  );
}
