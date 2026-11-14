// Voice helpers: record the microphone as 16 kHz mono WAV (what Sarvam's speech-to-text handles best),
// play synthesized speech, and fall back to the browser's built-in speech when Sarvam is not configured.

export interface VoiceLanguage {
  code: string;
  name: string;
  native: string;
}

export interface VoiceConfig {
  provider: "sarvam" | "browser";
  default_language: string;
  max_seconds: number;
  languages: VoiceLanguage[];
}

const WAV_RATE = 16000;

function encodeWav(samples: Float32Array, rate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, s: string) => [...s].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

/** Decode whatever the browser recorded (webm/mp4) and re-encode it as 16 kHz mono WAV. */
async function toWav(recorded: Blob): Promise<Blob> {
  const AC: typeof AudioContext = window.AudioContext || (window as any).webkitAudioContext;
  const ctx = new AC();
  try {
    const decoded = await ctx.decodeAudioData(await recorded.arrayBuffer());
    const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * WAV_RATE)), WAV_RATE);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination);
    source.start();
    const rendered = await offline.startRendering();
    return encodeWav(rendered.getChannelData(0), WAV_RATE);
  } finally {
    ctx.close().catch(() => {});
  }
}

export const canRecord = () => typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";

/** Microphone recorder. `start()` asks for permission; `stop()` resolves with a WAV blob. */
export class Recorder {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
    this.chunks = [];
    this.recorder = new MediaRecorder(this.stream);
    this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.recorder.start();
  }

  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const rec = this.recorder;
      if (!rec) return reject(new Error("Not recording"));
      rec.onstop = () => {
        const recorded = new Blob(this.chunks, { type: rec.mimeType });
        this.release();
        toWav(recorded).then(resolve, reject);
      };
      rec.stop();
    });
  }

  cancel(): void {
    try {
      this.recorder?.stop();
    } catch {
      /* already stopped */
    }
    this.release();
  }

  private release(): void {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.recorder = null;
  }
}

// ── Browser fallback (no Sarvam key): Web Speech API, available in Chrome and Edge ──

const SR: any = typeof window !== "undefined" ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition : null;
export const canBrowserRecognize = () => !!SR;

/** One-shot browser speech recognition. `stop()` ends listening; `result` resolves with the transcript. */
export class BrowserRecognizer {
  private rec: any;
  result: Promise<string>;

  constructor(language: string) {
    this.rec = new SR();
    this.rec.lang = language;
    this.rec.continuous = true;
    this.rec.interimResults = false;
    let text = "";
    this.result = new Promise((resolve, reject) => {
      this.rec.onresult = (e: any) => {
        for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) text += e.results[i][0].transcript + " ";
      };
      this.rec.onerror = (e: any) => (e.error === "no-speech" || e.error === "aborted" ? resolve(text.trim()) : reject(new Error(e.error)));
      this.rec.onend = () => resolve(text.trim());
    });
    this.rec.start();
  }

  stop(): void {
    this.rec.stop();
  }
}

// ── Playback ──

let current: HTMLAudioElement | null = null;
let currentUrl: string | null = null;

export function stopSpeaking(): void {
  if (current) {
    current.pause();
    current = null;
  }
  if (currentUrl) {
    URL.revokeObjectURL(currentUrl);
    currentUrl = null;
  }
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
}

/** Play base64 audio returned by the server. Resolves when playback ends or is stopped. */
export function playBase64(audioBase64: string, mime: string): Promise<void> {
  stopSpeaking();
  const bytes = Uint8Array.from(atob(audioBase64), (c) => c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: mime }));
  const audio = new Audio(url);
  current = audio;
  currentUrl = url;
  return new Promise((resolve, reject) => {
    audio.onended = () => resolve();
    audio.onpause = () => resolve();
    audio.onerror = () => reject(new Error("Could not play the audio"));
    audio.play().catch(reject);
  });
}

/** Speak with the browser's own voices (used when Sarvam is not configured or fails). */
export function browserSpeak(text: string, language: string): Promise<void> {
  stopSpeaking();
  if (typeof speechSynthesis === "undefined") return Promise.reject(new Error("This browser cannot speak"));
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = language;
    const voice = speechSynthesis.getVoices().find((v) => v.lang.replace("_", "-").toLowerCase().startsWith(language.slice(0, 2)));
    if (voice) u.voice = voice;
    u.rate = 0.95;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    speechSynthesis.speak(u);
  });
}

// ── Remembered language ──

const LANG_KEY = "yhg_language";
export const languageStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(LANG_KEY);
    } catch {
      return null;
    }
  },
  set: (code: string) => {
    try {
      localStorage.setItem(LANG_KEY, code);
    } catch {
      /* storage unavailable */
    }
  },
};
