import type { AudioDevice } from "@/lib/types";

type SinkCapableAudioElement = HTMLMediaElement & {
  setSinkId?: (sinkId: string) => Promise<void>;
  sinkId?: string;
};

export type AudioDeviceChangeListener = (devices: AudioDevice[]) => void;

export interface AudioDeviceManager {
  requestInputPermission(): Promise<void>;
  listInputDevices(): Promise<AudioDevice[]>;
  listOutputDevices(): Promise<AudioDevice[]>;
  selectInput(id: string): Promise<void>;
  selectOutput(id: string): Promise<void>;
  getSelectedInput(): AudioDevice | null;
  getSelectedOutput(): AudioDevice | null;
  setOutputElement(element: HTMLMediaElement | null): Promise<boolean>;
  subscribeToChanges(listener: AudioDeviceChangeListener): () => void;
  dispose(): void;
  canSelectOutput(): boolean;
}

function mediaDevicesOrThrow(): MediaDevices {
  if (typeof navigator === "undefined" || !navigator.mediaDevices) {
    throw new Error("Este navegador não disponibiliza dispositivos de áudio.");
  }
  return navigator.mediaDevices;
}

function labelFor(device: MediaDeviceInfo, index: number): string {
  if (device.label.trim()) return device.label;
  const kind = device.kind === "audioinput" ? "Microfone" : "Saída de áudio";
  return `${kind} ${index + 1}`;
}

export class BrowserAudioDeviceManager implements AudioDeviceManager {
  private selectedInputId: string | null = null;
  private selectedOutputId: string | null = null;
  private outputElement: SinkCapableAudioElement | null = null;
  private readonly listeners = new Set<AudioDeviceChangeListener>();
  private readonly handleDeviceChange = () => {
    void this.notifyDeviceChange();
  };

  constructor() {
    if (typeof navigator !== "undefined" && navigator.mediaDevices) {
      navigator.mediaDevices.addEventListener?.(
        "devicechange",
        this.handleDeviceChange,
      );
    }
  }

  async requestInputPermission(): Promise<void> {
    const stream = await mediaDevicesOrThrow().getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
  }

  async listInputDevices(): Promise<AudioDevice[]> {
    return this.listByKind("audioinput");
  }

  async listOutputDevices(): Promise<AudioDevice[]> {
    return this.listByKind("audiooutput");
  }

  async selectInput(id: string): Promise<void> {
    this.selectedInputId = id;
  }

  async selectOutput(id: string): Promise<void> {
    this.selectedOutputId = id;
    await this.applyOutputToElement();
  }

  getSelectedInput(): AudioDevice | null {
    return this.selectedInputId
      ? {
          deviceId: this.selectedInputId,
          groupId: "",
          label: "",
          kind: "audioinput",
        }
      : null;
  }

  getSelectedOutput(): AudioDevice | null {
    return this.selectedOutputId
      ? {
          deviceId: this.selectedOutputId,
          groupId: "",
          label: "",
          kind: "audiooutput",
        }
      : null;
  }

  async setOutputElement(element: HTMLMediaElement | null): Promise<boolean> {
    this.outputElement = element as SinkCapableAudioElement | null;
    return this.applyOutputToElement();
  }

  subscribeToChanges(listener: AudioDeviceChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  dispose(): void {
    if (typeof navigator !== "undefined" && navigator.mediaDevices) {
      navigator.mediaDevices.removeEventListener?.(
        "devicechange",
        this.handleDeviceChange,
      );
    }
    this.listeners.clear();
    this.outputElement = null;
  }

  canSelectOutput(): boolean {
    return Boolean(this.outputElement?.setSinkId);
  }

  private async listByKind(
    kind: "audioinput" | "audiooutput",
  ): Promise<AudioDevice[]> {
    const devices = await mediaDevicesOrThrow().enumerateDevices();
    return devices
      .filter((device) => device.kind === kind)
      .map((device, index) => ({
        deviceId: device.deviceId,
        groupId: device.groupId,
        label: labelFor(device, index),
        kind,
      }));
  }

  private async notifyDeviceChange(): Promise<void> {
    const devices = await this.listInputDevices().catch(() => []);
    const outputs = await this.listOutputDevices().catch(() => []);
    const all = [...devices, ...outputs];
    this.listeners.forEach((listener) => listener(all));
  }

  private async applyOutputToElement(): Promise<boolean> {
    if (!this.outputElement?.setSinkId || this.selectedOutputId === null) {
      return false;
    }
    try {
      await this.outputElement.setSinkId(this.selectedOutputId);
      return true;
    } catch {
      return false;
    }
  }
}

