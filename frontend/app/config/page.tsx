"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Save, RotateCcw, Mic, Wrench, Globe, Brain, Settings, Loader2, ShieldCheck, LogOut } from "lucide-react";
import { useToast } from "@/components/ui/toast";

const DEFAULT_SYSTEM_PROMPT = `Você é a Sophie, assistente pessoal de inteligência artificial do Wanderson. Fala sempre em português brasileiro, com tom profissional, elegante e direto, inspirado no JARVIS: nunca invente fatos, admita quando não souber, e use humor sutil quando apropriado. Trate o usuário como 'chefe'. Seja conciso: prefira respostas curtas e úteis, em vez de longas explicações. Nunca repita o que o usuário acabou de dizer.`;

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

interface ActiveSession {
  session_id: string;
  current: boolean;
  device_id: string | null;
  device_name: string | null;
  device_type: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
}

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
  tools_enabled: [],
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
    <div className={`glass animate-fade-up p-5 sm:p-6 rounded-2xl ${className}`}>
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
        aria-label={label}
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

function Toggle({
  label,
  desc,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  desc: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-start gap-4 cursor-pointer group has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60">
      <div className="relative mt-1">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
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
  const [offline, setOffline] = useState(false);
  const [promptChars, setPromptChars] = useState(DEFAULT_SYSTEM_PROMPT.length);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/proxy/brain/config", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        const loaded = data?.config ?? data;
        setConfig({ ...DEFAULT_CONFIG, ...loaded });
        setPromptChars(
          loaded?.system_prompt?.length ?? DEFAULT_SYSTEM_PROMPT.length
        );
        setOffline(false);
      } else {
        setOffline(true);
      }
    } catch (e) {
      console.warn("Config fetch failed:", e);
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/proxy/security/sessions", { cache: "no-store" });
      if (!res.ok) throw new Error("Falha ao carregar sessões");
      setSessions((await res.json()) as ActiveSession[]);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchConfig();
    void fetchSessions();
  }, [fetchConfig, fetchSessions]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/proxy/brain/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system_prompt: config.system_prompt,
          temperature: config.temperature,
          max_tokens: config.max_tokens,
        }),
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

  const revokeSession = async (sessionId: string) => {
    if (!window.confirm("Revogar esta sessão? O dispositivo perderá acesso imediatamente.")) {
      return;
    }
    const res = await fetch(`/api/proxy/security/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    if (res.ok) {
      toast({
        title: "Sessão revogada",
        description: "O dispositivo foi desconectado.",
        variant: "success",
      });
      await fetchSessions();
    } else {
      toast({
        title: "Falha ao revogar sessão",
        description: "A sessão não pôde ser encerrada.",
        variant: "destructive",
      });
    }
  };

  const revokeOtherSessions = async () => {
    if (!window.confirm("Encerrar todas as outras sessões e manter somente esta?")) {
      return;
    }
    const res = await fetch("/api/proxy/security/sessions/revoke-others", {
      method: "POST",
    });
    if (res.ok) {
      const data = (await res.json()) as { revoked?: number };
      toast({
        title: "Outras sessões encerradas",
        description: `${data.revoked ?? 0} sessão(ões) revogada(s).`,
        variant: "success",
      });
      await fetchSessions();
    } else {
      toast({
        title: "Falha ao encerrar sessões",
        description: "Não foi possível revogar as outras sessões.",
        variant: "destructive",
      });
    }
  };


  if (loading) {
    return (
      <main className="flex min-h-[60vh] items-center justify-center px-4">
        <div className="flex flex-col items-center gap-4">
          <div className="size-10 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          <p className="text-[var(--text-secondary)]">Carregando configuração...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-6 sm:py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-[var(--text-primary)]">Configuração da Sophie</h1>
          <p className="text-[var(--text-secondary)] mt-1">Personalize o comportamento da Sophie; infraestrutura e integrações são somente leitura</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving || offline}
          className="glass glass-hover interactive-control flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-[var(--text-primary)] hover:bg-[var(--accent-muted)] transition-colors disabled:opacity-50"
        >
          <Save className="size-5" />
          <span>{saving ? "Salvando..." : "Salvar alterações"}</span>
          {saving && <Loader2 className="size-5 animate-spin" />}
        </button>
      </div>

      {offline && (
        <div className="glass flex items-center gap-3 rounded-2xl border-[#F59E0B]/40 px-4 py-3">
          <Settings className="size-4 shrink-0 text-[#F59E0B]" />
          <p className="text-sm text-[#F59E0B]">
            Backend inacessível — exibindo valores padrão. O salvamento só
            funcionará quando o servidor voltar.
          </p>
        </div>
      )}

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
              className="w-full min-h-[160px] font-mono-data text-base sm:text-sm bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-y"
              placeholder="Defina a personalidade da Sophie..."
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
                  aria-label="Modelo Principal"
                  value={config.primary_model}
                  disabled
                  className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  {MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Modelo Fallback</label>
                <select
                  aria-label="Modelo Fallback"
                  value={config.fallback_model}
                  disabled
                  className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  {MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
              Modelos são definidos pelo ambiente do servidor e não podem ser alterados nesta tela.
            </p>
            <Slider label="Temperatura" value={config.temperature} min={0} max={2} step={0.1} onChange={v => setConfig(prev => ({ ...prev, temperature: v }))} />
            <Slider label="Max Tokens" value={config.max_tokens} min={1} max={8192} step={1} onChange={v => setConfig(prev => ({ ...prev, max_tokens: v }))} unit=" tokens" />
          </div>
        </SectionCard>

        <SectionCard title="Ferramentas" icon={Wrench}>
          <p className="mb-4 text-xs leading-relaxed text-[var(--text-secondary)]">
            Integrações ainda não habilitadas no Tool Manager aparecem somente como referência.
          </p>
          <div className="space-y-3">
            {TOOL_OPTIONS.map(tool => (
              <label key={tool.id} className="glass flex items-center gap-3 rounded-xl p-3 opacity-70">
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
                  disabled
                  readOnly
                  className="peer size-5 appearance-none rounded-lg border-2 border-[var(--border)] bg-[var(--bg-secondary)] checked:bg-[var(--accent)] checked:border-[var(--accent)] transition-colors"
                />
              </label>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Voz" icon={Mic}>
          <p className="mb-4 text-xs leading-relaxed text-[var(--text-secondary)]">
            Voz e STT são gerenciados por variáveis do servidor para evitar alterações inseguras em runtime.
          </p>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Toggle
                label="TTS (Fala da Sophie)"
                desc="Respostas em áudio automáticas"
                checked={config.voice.tts_enabled}
                onChange={() => undefined}
                disabled
              />
              <Toggle
                label="STT (Reconhecimento de Voz)"
                desc="Microfone para falar com a Sophie"
                checked={config.voice.stt_enabled}
                onChange={() => undefined}
                disabled
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Voz (edge-tts)</label>
              <select
                aria-label="Voz do edge-tts"
                value={config.voice.voice}
                disabled
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                {VOICE_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Velocidade</label>
              <select
                aria-label="Velocidade da fala"
                value={config.voice.rate}
                disabled
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                {RATE_OPTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Sessões e dispositivos" icon={ShieldCheck}>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-[var(--text-secondary)]">
                Revogue acessos que você não reconhece. Tokens nunca são exibidos nesta tela.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void revokeOtherSessions()}
              disabled={sessionsLoading || sessions.filter(session => !session.current).length === 0}
              className="glass glass-hover interactive-control inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm text-[var(--color-warn)] disabled:opacity-50"
            >
              <LogOut className="size-4" />
              Encerrar outras sessões
            </button>
          </div>

          <div className="space-y-3">
            {sessionsLoading ? (
              <p className="text-sm text-[var(--text-secondary)]">Carregando sessões...</p>
            ) : sessions.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">
                Nenhuma sessão ativa foi encontrada.
              </p>
            ) : (
              sessions.map(session => (
                <div
                  key={session.session_id}
                  className="flex flex-col gap-3 rounded-xl border border-[var(--border)] p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-[var(--text-primary)]">
                        {session.device_name || "Dispositivo desconhecido"}
                      </p>
                      {session.current ? (
                        <span className="rounded-full bg-[var(--accent-muted)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">
                          sessão atual
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      {session.device_type || "tipo não informado"} · último uso{" "}
                      {new Date(session.last_seen_at).toLocaleString("pt-BR")}
                    </p>
                    <p className="mt-1 font-mono-data text-[10px] text-[var(--text-secondary)]">
                      expira {new Date(session.expires_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                  {!session.current ? (
                    <button
                      type="button"
                      onClick={() => void revokeSession(session.session_id)}
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--color-danger)]/30 px-3 py-2 text-sm text-[var(--color-danger)]"
                    >
                      <LogOut className="size-4" />
                      Revogar
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      </SectionCard>

      <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border)]">
        <button
          onClick={() => router.back()}
          className="glass glass-hover interactive-control px-6 py-3 rounded-xl font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-muted)] transition-colors"
        >
          Voltar
        </button>
        <button
          onClick={handleSave}
          disabled={saving || offline}
          className="interactive-control flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-[var(--bg-primary)] bg-[var(--accent)] hover:bg-[var(--accent-glow)] transition-colors disabled:opacity-50"
        >
          <Save className="size-5" />
          <span>{saving ? "Salvando..." : "Salvar alterações"}</span>
          {saving && <Loader2 className="size-5 animate-spin" />}
        </button>
      </div>
    </main>
  );
}
