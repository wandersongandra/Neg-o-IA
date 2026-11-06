"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import Image from "next/image";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export type AvatarState = "idle" | "thinking" | "speaking" | "listening" | "error";

export interface AvatarCoreRef {
  setState: (state: AvatarState) => void;
  speak: (audio: HTMLAudioElement) => void;
  stopSpeaking: () => void;
}

const STATE_COLOR: Record<AvatarState, number> = {
  idle: 0xa84230,
  thinking: 0xd6a04b,
  speaking: 0xd85a3d,
  listening: 0x65a885,
  error: 0xbf4545,
};

export const AvatarCore = forwardRef<
  AvatarCoreRef,
  { className?: string; "aria-hidden"?: boolean | "true" | "false" }
>((props, ref) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef<AvatarState>("idle");
  const jawRef = useRef<THREE.Object3D | null>(null);
  const headRef = useRef<THREE.Object3D | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const audioSourcesRef = useRef<WeakMap<HTMLAudioElement, MediaElementAudioSourceNode>>(new WeakMap());
  const speakingRef = useRef(false);
  const [state, setState] = useState<AvatarState>("idle");
  const [failed, setFailed] = useState(false);

  const setAvatarState = useCallback((next: AvatarState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const speak = useCallback((audio: HTMLAudioElement) => {
    try {
      const Ctx = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctx) throw new Error("Web Audio is not supported");
      const context = audioContextRef.current ?? new Ctx();
      audioContextRef.current = context;
      const source = audioSourcesRef.current.get(audio) ?? context.createMediaElementSource(audio);
      audioSourcesRef.current.set(audio, source);
      sourceRef.current?.disconnect();
      analyserRef.current?.disconnect();
      sourceRef.current = source;
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.78;
      source.connect(analyser);
      analyser.connect(context.destination);
      analyserRef.current = analyser;
      if (context.state === "suspended") void context.resume();
      speakingRef.current = true;
      setAvatarState("speaking");
      void audio.play().catch(() => {
        speakingRef.current = false;
        setAvatarState("idle");
      });
      const data = new Uint8Array(analyser.frequencyBinCount);
      const update = () => {
        if (!speakingRef.current) return;
        analyser.getByteFrequencyData(data);
        const mean = data.slice(0, 32).reduce((sum, value) => sum + value, 0) / 32 / 255;
        if (jawRef.current) jawRef.current.rotation.x = -Math.min(mean * 0.27, 0.18);
        if (!audio.paused && !audio.ended) requestAnimationFrame(update);
        else {
          speakingRef.current = false;
          if (jawRef.current) jawRef.current.rotation.x = 0;
          source.disconnect();
          analyser.disconnect();
          if (sourceRef.current === source) sourceRef.current = null;
          if (analyserRef.current === analyser) analyserRef.current = null;
          setAvatarState("idle");
        }
      };
      update();
    } catch (error) {
      console.warn("Avatar speech animation unavailable:", error);
      setAvatarState("speaking");
    }
  }, [setAvatarState]);

  const stopSpeaking = useCallback(() => {
    speakingRef.current = false;
    if (jawRef.current) jawRef.current.rotation.x = 0;
    sourceRef.current?.disconnect();
    analyserRef.current?.disconnect();
    analyserRef.current = null;
    setAvatarState("idle");
  }, [setAvatarState]);

  useImperativeHandle(ref, () => ({ setState: setAvatarState, speak, stopSpeaking }), [setAvatarState, speak, stopSpeaking]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let disposed = false;
    let frame = 0;
    let frameTimer: number | null = null;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "low-power" });
    } catch {
      setFailed(true);
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 30);
    camera.position.set(0, 0.05, 4.5);
    scene.add(new THREE.HemisphereLight(0xd8d5cd, 0x1c2021, 2.0));
    const key = new THREE.DirectionalLight(0xffe9d0, 3.3);
    key.position.set(-3, 4, 5);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x8f9b9d, 1.2);
    fill.position.set(4, 0, 2);
    scene.add(fill);
    const rim = new THREE.DirectionalLight(0xc34b32, 1.8);
    rim.position.set(0, 2, -3);
    scene.add(rim);
    const pointer = new THREE.Vector2();
    const target = new THREE.Vector2();
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      renderer.setSize(rect.width, rect.height, false);
      camera.aspect = rect.width / rect.height;
      camera.updateProjectionMatrix();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();
    const onPointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      target.x = ((event.clientX - rect.left) / rect.width - 0.5) * 0.35;
      target.y = ((event.clientY - rect.top) / rect.height - 0.5) * 0.22;
    };
    const onPointerLeave = () => target.set(0, 0);
    canvas.addEventListener("pointermove", onPointerMove, { passive: true });
    canvas.addEventListener("pointerleave", onPointerLeave, { passive: true });

    const loader = new GLTFLoader();
    loader.load("/models/sentinel.glb", (gltf) => {
      if (disposed) return;
      const root = gltf.scene;
      scene.add(root);
      headRef.current = root.getObjectByName("HeadPivot") ?? root;
      jawRef.current = root.getObjectByName("JawPivot") ?? null;
      root.rotation.y = 0;
      const bounds = new THREE.Box3().setFromObject(root);
      const center = bounds.getCenter(new THREE.Vector3());
      root.position.sub(center);
      // Keep the neck visible but give the face most of the viewport.
      root.scale.setScalar(1.12);
    }, undefined, (error) => {
      console.error("Could not load sentinel GLB:", error);
      if (!disposed) setFailed(true);
    });

    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      const elapsed = clock.getElapsedTime();
      const active = stateRef.current;
      const head = headRef.current;
      if (head) {
        pointer.lerp(target, 0.035);
        const motion = reducedMotion.matches ? 0 : 1;
        const amplitude = active === "thinking" ? 0.11 : active === "listening" ? 0.07 : 0.045;
        head.rotation.y = pointer.x * motion + Math.sin(elapsed * 0.42) * amplitude * motion;
        head.rotation.x = pointer.y * motion + Math.sin(elapsed * 0.7) * 0.018 * motion;
        head.position.y = Math.sin(elapsed * 0.8) * 0.025 * motion;
      }
      const color = STATE_COLOR[active];
      for (const light of [key, rim]) light.color.setHex(active === "idle" ? (light === key ? 0xffe9d0 : color) : color);
      renderer.render(scene, camera);
      frameTimer = window.setTimeout(
        () => { frame = requestAnimationFrame(animate); },
        reducedMotion.matches ? 80 : 33,
      );
    };
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      if (frameTimer !== null) window.clearTimeout(frameTimer);
      resizeObserver.disconnect();
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        if (mesh.material) {
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      headRef.current = null;
      jawRef.current = null;
    };
  }, []);

  return (
    <div className="relative h-full w-full" aria-hidden={props["aria-hidden"] ?? true}>
      <canvas ref={canvasRef} className={props.className ?? "h-full w-full"} aria-label={`Avatar mecânico — ${state}`} role="img" />
      {failed ? <Image src="/models/sentinel.webp" alt="" fill sizes="(max-width: 640px) 90vw, 480px" className="object-contain" /> : null}
    </div>
  );
});

AvatarCore.displayName = "AvatarCore";
export default AvatarCore;
