"use client";

import { createContext, useContext, useRef, useState, useCallback } from "react";
import type { AvatarCoreRef } from "./avatar-core";

interface AvatarContextType {
  state: "idle" | "thinking" | "speaking" | "listening" | "error";
  setState: (state: "idle" | "thinking" | "speaking" | "listening" | "error") => void;
  speak: (audio: HTMLAudioElement) => void;
  stopSpeaking: () => void;
  registerRef: (ref: AvatarCoreRef | null) => void;
}

const AvatarContext = createContext<AvatarContextType | null>(null);

export function AvatarProvider({ children }: { children: React.ReactNode }) {
  const avatarRef = useRef<AvatarCoreRef | null>(null);
  const [state, setStateInternal] = useState<"idle" | "thinking" | "speaking" | "listening" | "error">("idle");

  const registerRef = useCallback((ref: AvatarCoreRef | null) => {
    avatarRef.current = ref;
  }, []);

  const speak = useCallback((audio: HTMLAudioElement) => {
    avatarRef.current?.speak(audio);
  }, []);

  const stopSpeaking = useCallback(() => {
    avatarRef.current?.stopSpeaking();
  }, []);

  const setState = useCallback((newState: "idle" | "thinking" | "speaking" | "listening" | "error") => {
    avatarRef.current?.setState(newState);
    setStateInternal(newState);
  }, []);

  return (
    <AvatarContext.Provider value={{ state, setState, speak, stopSpeaking, registerRef }}>
      {children}
    </AvatarContext.Provider>
  );
}

export function useAvatar() {
  const context = useContext(AvatarContext);
  if (!context) {
    throw new Error("useAvatar must be used within an AvatarProvider");
  }
  return context;
}

export { AvatarContext };