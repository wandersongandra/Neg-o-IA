"use client";

import type { BrainStatus, DashboardData } from "@/lib/types";
import { AvatarCore, type AvatarCoreRef } from "./avatar/avatar-core";
import { useAvatar } from "./avatar/avatar-context";
import { useRef, useImperativeHandle, forwardRef, useEffect } from "react";

interface CoreSphereProps {
  data: DashboardData | null;
  brain: BrainStatus | null;
}

export interface CoreSphereRef {
  setState: (state: "idle" | "thinking" | "speaking" | "listening" | "error") => void;
  speak: (audio: HTMLAudioElement) => void;
  stopSpeaking: () => void;
}

const STATUS_COPY = {
  idle: "SISTEMA EM ESPERA",
  thinking: "PROCESSANDO ENTRADA",
  speaking: "RESPOSTA EMITIDA",
  listening: "CAPTURA DE VOZ",
  error: "SINAL INTERROMPIDO",
} as const;

export const CoreSphere = forwardRef<CoreSphereRef, CoreSphereProps>(
  ({ data, brain }, ref) => {
    const avatarRef = useRef<AvatarCoreRef>(null);
    const { registerRef, state } = useAvatar();

    useEffect(() => {
      registerRef(avatarRef.current);
      return () => registerRef(null);
    }, [registerRef]);

    useImperativeHandle(ref, () => ({
      setState: (state) => avatarRef.current?.setState(state),
      speak: (audio) => avatarRef.current?.speak(audio),
      stopSpeaking: () => avatarRef.current?.stopSpeaking(),
    }));

    const online = data?.healthz?.status === "alive" || data?.healthz?.status === "ok";
    const latency = data?.latency_ms;
    return (
      <div
        className="ultron-core relative mx-auto flex aspect-square w-full max-w-[480px] items-center justify-center overflow-hidden"
        aria-label={`Sentinel da Ultron — ${online ? "online" : "offline"}`}
      >
        <div className="absolute inset-x-[12%] bottom-[15%] h-[2px] rounded-full bg-white/10" aria-hidden="true" />
        <AvatarCore
          ref={avatarRef}
          className="absolute inset-[4%] h-[92%] w-[92%]"
          aria-hidden="true"
        />
        <div className="absolute bottom-[5%] left-1/2 z-30 -translate-x-1/2 text-center">
          <p className="text-[11px] font-semibold tracking-[0.24em] text-[#e7e4dd]">ULTRON</p>
          <p className="mt-1 text-[9px] tracking-[0.12em] text-white/55">{STATUS_COPY[state]}</p>
        </div>
        <div className="absolute left-[5%] top-[41%] z-30 text-[9px] tracking-[0.08em] text-white/55">
          <span className="block font-medium text-[#ca6148]">NÚCLEO 01</span>
          <span className="mt-1 block">{online ? "CONECTADO" : "OFFLINE"}</span>
        </div>
        <div className="absolute right-[5%] top-[41%] z-30 text-right text-[9px] tracking-[0.08em] text-white/55">
          <span className="block max-w-24 truncate font-medium text-[#ca6148]">{brain?.primary_model ?? "NÚCLEO NEURAL"}</span>
          <span className="mt-1 block">{latency == null ? "—" : `${latency} MS`}</span>
        </div>
      </div>
    );
  }
);

CoreSphere.displayName = "CoreSphere";

export default CoreSphere;
