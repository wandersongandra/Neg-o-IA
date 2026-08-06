"use client";

import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from "react";

export type AvatarState = "idle" | "thinking" | "speaking" | "listening" | "error";

export interface AvatarCoreRef {
  setState: (state: AvatarState) => void;
  speak: (audio: HTMLAudioElement) => void;
  stopSpeaking: () => void;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  layer: number;
  baseRadius: number;
  angle: number;
  orbitRadius: number;
  orbitSpeed: number;
  orbitAngle: number;
}

const LAYER_CONFIG = [
  { count: 30, radius: 0.35, speed: 0.0008, size: 1.5 },
  { count: 40, radius: 0.55, speed: 0.0005, size: 1.0 },
  { count: 50, radius: 0.75, speed: 0.0003, size: 0.6 },
];

const STATE_COLORS = {
  idle: { primary: "var(--accent)", glow: "var(--accent-glow)", particle: "var(--accent-glow)" },
  thinking: { primary: "var(--color-warn)", glow: "var(--color-warn)", particle: "var(--color-warn)" },
  speaking: { primary: "var(--accent)", glow: "var(--accent-glow)", particle: "var(--accent)" },
  listening: { primary: "var(--color-ok)", glow: "var(--color-ok)", particle: "var(--color-ok)" },
  error: { primary: "var(--color-danger)", glow: "var(--color-danger)", particle: "var(--color-danger)" },
};

export const AvatarCore = forwardRef<AvatarCoreRef, { className?: string; "aria-hidden"?: boolean | "true" | "false" }>((
  (props, ref) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(-1);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const dataArrayRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const reducedMotion = useRef(false);

  const [state, setStateInternal] = useState<AvatarState>("idle");
  const [particles, setParticles] = useState<Particle[]>([]);
  const [mouthOpen, setMouthOpen] = useState(0);
  const [pulsePhase, setPulsePhase] = useState(0);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotion.current = mediaQuery.matches;
    const handler = (e: MediaQueryListEvent) => { reducedMotion.current = e.matches; };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const initParticles = useCallback(() => {
    const newParticles: Particle[] = [];
    LAYER_CONFIG.forEach((layer, layerIndex) => {
      for (let i = 0; i < layer.count; i++) {
        const angle = (i / layer.count) * Math.PI * 2;
        newParticles.push({
          x: 0, y: 0,
          vx: 0, vy: 0,
          radius: layer.size * (0.5 + Math.random() * 0.5),
          baseRadius: layer.size * (0.5 + Math.random() * 0.5),
          layer: layerIndex,
          angle,
          orbitRadius: layer.radius * (0.7 + Math.random() * 0.3),
          orbitSpeed: layer.speed * (0.5 + Math.random() * 0.5),
          orbitAngle: Math.random() * Math.PI * 2,
        });
      }
    });
    setParticles(newParticles);
  }, []);

  useEffect(() => {
    initParticles();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    let lastTime = performance.now();

    const animate = (time: number) => {
      if (reducedMotion.current) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      const dt = time - lastTime;
      lastTime = time;

      const width = canvas.width / (window.devicePixelRatio || 1);
      const height = canvas.height / (window.devicePixelRatio || 1);
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) * 0.45;

      ctx.clearRect(0, 0, width, height);

      const colors = STATE_COLORS[state];
      const primaryColor = getComputedStyle(document.documentElement).getPropertyValue(colors.primary.replace("var(", "").replace(")", "")).trim() || colors.primary;
      const glowColor = getComputedStyle(document.documentElement).getPropertyValue(colors.glow.replace("var(", "").replace(")", "")).trim() || colors.glow;
      const particleColor = getComputedStyle(document.documentElement).getPropertyValue(colors.particle.replace("var(", "").replace(")", "")).trim() || colors.particle;

      // Pulse phase
      setPulsePhase(prev => (prev + dt * 0.001) % (Math.PI * 2));

      // Core glow
      const pulse = Math.sin(pulsePhase) * 0.15 + 0.85;
      const coreRadius = radius * pulse;
      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreRadius * 1.5);
      gradient.addColorStop(0, `${primaryColor}40`);
      gradient.addColorStop(0.5, `${primaryColor}20`);
      gradient.addColorStop(1, "transparent");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(cx, cy, coreRadius * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Core border
      ctx.strokeStyle = `${primaryColor}80`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
      ctx.stroke();

      // Mouth animation when speaking
      if (state === "speaking") {
        const mouthHeight = mouthOpen * radius * 0.3;
        ctx.strokeStyle = `${primaryColor}CC`;
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(cx - radius * 0.3, cy + radius * 0.1);
        ctx.quadraticCurveTo(cx, cy + radius * 0.1 + mouthHeight, cx + radius * 0.3, cy + radius * 0.1);
        ctx.stroke();
      }

      // Update and draw particles
      setParticles(prev => prev.map(p => {
        const layerConfig = LAYER_CONFIG[p.layer];
        let orbitRadius = p.orbitRadius * radius;
        let orbitSpeed = p.orbitSpeed;

        if (state === "thinking") {
          orbitSpeed *= 3;
          orbitRadius *= 0.6 + Math.sin(time * 0.002 + p.orbitAngle) * 0.2;
        } else if (state === "speaking") {
          orbitSpeed *= 1.5;
          orbitRadius *= 1 + Math.sin(time * 0.005 + p.orbitAngle) * 0.15;
        } else if (state === "listening") {
          orbitSpeed *= 0.5;
          orbitRadius *= 1 + Math.sin(time * 0.003 + p.orbitAngle) * 0.1;
        } else if (state === "error") {
          orbitSpeed *= 2;
          orbitRadius *= 1 + Math.sin(time * 0.01 + p.orbitAngle) * 0.3;
        }

        p.orbitAngle += orbitSpeed * dt;
        p.x = cx + Math.cos(p.orbitAngle) * orbitRadius;
        p.y = cy + Math.sin(p.orbitAngle) * orbitRadius;

        // Converge to center when thinking
        if (state === "thinking") {
          const dx = cx - p.x;
          const dy = cy - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 20) {
            p.x += dx * 0.02;
            p.y += dy * 0.02;
          }
        }

        // Disperse on error
        if (state === "error") {
          const dx = p.x - cx;
          const dy = p.y - cy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < radius * 1.5) {
            p.x += dx * 0.01;
            p.y += dy * 0.01;
          }
        }

        // Draw particle
        const particleGradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 2);
        const particleHex = getComputedStyle(document.documentElement).getPropertyValue(colors.particle.replace("var(", "").replace(")", "")).trim() || particleColor;
        particleGradient.addColorStop(0, `${particleHex}FF`);
        particleGradient.addColorStop(1, `${particleHex}00`);
        ctx.fillStyle = particleGradient;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        // Connections for thinking state
        if (state === "thinking") {
          return p;
        }

        return p;
      }));

      // Draw connections for thinking
      if (state === "thinking") {
        ctx.strokeStyle = `${particleColor}30`;
        ctx.lineWidth = 0.5;
        particles.forEach((p1, i) => {
          particles.slice(i + 1).forEach(p2 => {
            const dx = p1.x - p2.x;
            const dy = p1.y - p2.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 120) {
              ctx.globalAlpha = 1 - dist / 120;
              ctx.beginPath();
              ctx.moveTo(p1.x, p1.y);
              ctx.lineTo(p2.x, p2.y);
              ctx.stroke();
            }
          });
        });
        ctx.globalAlpha = 1;
      }

      // Outer ring
      ctx.strokeStyle = `${primaryColor}40`;
      ctx.lineWidth = 1;
      ctx.setLineDash([10, 10]);
      ctx.lineDashOffset = time * 0.02;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.1, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [state, initParticles]);

  const setState = useCallback((newState: AvatarState) => {
    setStateInternal(newState);
  }, []);

  const speak = useCallback((audio: HTMLAudioElement) => {
    try {
      if (!audioContextRef.current) {
        const AudioCtx = (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext) as typeof AudioContext;
        audioContextRef.current = new AudioCtx();
      }
      if (audioContextRef.current.state === "suspended") {
        audioContextRef.current.resume();
      }
      if (sourceRef.current) {
        sourceRef.current.disconnect();
      }
      sourceRef.current = audioContextRef.current.createMediaElementSource(audio);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;
      sourceRef.current.connect(analyserRef.current);
      analyserRef.current.connect(audioContextRef.current.destination);
      dataArrayRef.current = new Uint8Array(analyserRef.current.frequencyBinCount);

      setStateInternal("speaking");

      const updateMouth = () => {
        if (!analyserRef.current || !dataArrayRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArrayRef.current!);
        let sum = 0;
        for (let i = 0; i < 32; i++) sum += dataArrayRef.current[i];
        const avg = sum / 32 / 255;
        setMouthOpen(Math.min(avg * 2, 1));
        if (!audio.paused && !audio.ended) {
          requestAnimationFrame(updateMouth);
        } else {
          setMouthOpen(0);
          setStateInternal("idle");
        }
      };
      updateMouth();
    } catch (e) {
      console.warn("Avatar lip-sync failed:", e);
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    setMouthOpen(0);
    setStateInternal("idle");
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }
  }, []);

  useImperativeHandle(ref, () => ({
    setState,
    speak,
    stopSpeaking,
  }));

  return (
     <canvas
      ref={canvasRef}
      className={`w-full h-full max-w-[480px] max-h-[480px] ${props.className || ""}`}
      aria-hidden={props["aria-hidden"]}
      aria-label={`Avatar NEGÃO — estado: ${state}`}
      role="img"
    />
  );
}));

AvatarCore.displayName = "AvatarCore";