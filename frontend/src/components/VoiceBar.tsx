import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { LoaderCircle, Mic, Square, Volume2, VolumeX } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { BrowserRecognizer, canBrowserRecognize, canRecord, Recorder, type VoiceConfig } from "../lib/voice";

type Phase = "idle" | "recording" | "transcribing";

const LABELS: Record<string, Record<string, string>> = {
  "hi-IN": {
    idle: "बोलने के लिए माइक दबाएं",
    recording: "सुन रहा हूं… बोलकर फिर से दबाएं",
    transcribing: "समझ रहा हूं…",
    thinking: "सोच रहा हूं…",
    speaking: "बोल रहा हूं… रोकने के लिए दबाएं",
    denied: "माइक की अनुमति नहीं मिली। कृपया ब्राउज़र में माइक चालू करें।",
    empty: "कुछ सुनाई नहीं दिया। कृपया फिर से बोलें।",
    unsupported: "इस ब्राउज़र में माइक नहीं चल रहा। कृपया लिखकर बताएं।",
  },
  default: {
    idle: "Tap the mic and speak",
    recording: "Listening… tap again when you finish",
    transcribing: "Understanding…",
    thinking: "Thinking…",
    speaking: "Speaking… tap to stop",
    denied: "Microphone permission was denied. Please allow the microphone in your browser.",
    empty: "I could not hear anything. Please try again.",
    unsupported: "The microphone is not available in this browser. Please type instead.",
  },
};

interface Props {
  config: VoiceConfig;
  language: string;
  onLanguage: (code: string) => void;
  /** Called with what the patient said. */
  onText: (text: string) => void;
  /** The agent is working on a reply. */
  busy: boolean;
  speaking: boolean;
  onStopSpeaking: () => void;
  autoSpeak: boolean;
  onAutoSpeak: (on: boolean) => void;
}

export default function VoiceBar({ config, language, onLanguage, onText, busy, speaking, onStopSpeaking, autoSpeak, onAutoSpeak }: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<Recorder | null>(null);
  const recognizer = useRef<BrowserRecognizer | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const L = LABELS[language] ?? LABELS.default;

  const useSarvam = config.provider === "sarvam" && canRecord();
  const supported = useSarvam || canBrowserRecognize();

  const clearTimer = () => {
    window.clearInterval(timer.current);
    timer.current = undefined;
  };

  useEffect(
    () => () => {
      clearTimer();
      recorder.current?.cancel();
      recognizer.current?.stop();
    },
    [],
  );

  const finish = async () => {
    clearTimer();
    setPhase("transcribing");
    try {
      let text = "";
      if (recorder.current) {
        const wav = await recorder.current.stop();
        recorder.current = null;
        text = (await api.transcribe(wav, language)).transcript;
      } else if (recognizer.current) {
        recognizer.current.stop();
        text = await recognizer.current.result;
        recognizer.current = null;
      }
      if (text.trim()) onText(text.trim());
      else setError(L.empty);
    } catch (e: any) {
      setError(e?.status === 422 ? L.empty : e?.message || L.empty);
    } finally {
      setPhase("idle");
    }
  };

  const start = async () => {
    setError("");
    onStopSpeaking();
    try {
      if (useSarvam) {
        recorder.current = new Recorder();
        await recorder.current.start();
      } else {
        recognizer.current = new BrowserRecognizer(language);
      }
    } catch {
      recorder.current = null;
      recognizer.current = null;
      setError(L.denied);
      return;
    }
    setSeconds(0);
    setPhase("recording");
    const began = Date.now();
    timer.current = window.setInterval(() => {
      const s = Math.floor((Date.now() - began) / 1000);
      setSeconds(s);
      if (s >= config.max_seconds) finish(); // the speech service takes short clips
    }, 250);
  };

  const onMic = () => {
    if (speaking) return onStopSpeaking();
    if (phase === "recording") return void finish();
    if (phase === "idle" && !busy) void start();
  };

  const status = !supported ? L.unsupported : speaking ? L.speaking : phase !== "idle" ? L[phase] : busy ? L.thinking : L.idle;
  const waiting = phase === "transcribing" || (busy && phase === "idle" && !speaking);

  return (
    <div className="glass flex items-center gap-4 rounded-[1.75rem] px-4 py-3">
      <div className="relative shrink-0">
        {phase === "recording" && (
          <motion.span className="absolute inset-0 rounded-full bg-red-400/40" animate={{ scale: [1, 1.5, 1], opacity: [0.7, 0, 0.7] }} transition={{ repeat: Infinity, duration: 1.4 }} />
        )}
        <button type="button" onClick={onMic} disabled={!supported || waiting} aria-label={status}
          className={clsx(
            "relative flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition hover:scale-105 disabled:opacity-50 disabled:hover:scale-100",
            phase === "recording" ? "bg-red-500 shadow-red-500/40" : speaking ? "bg-amber-500 shadow-amber-500/40" : "bg-gradient-to-br from-brand-500 to-brand-700 shadow-brand-600/40",
          )}>
          {waiting ? <LoaderCircle className="h-7 w-7 animate-spin" /> : phase === "recording" || speaking ? <Square className="h-6 w-6 fill-current" /> : <Mic className="h-7 w-7" />}
        </button>
      </div>

      <div className="min-w-0 flex-1" aria-live="polite">
        <p className={clsx("text-base font-semibold", error ? "text-red-600" : "text-slate-800")}>{error || status}</p>
        <p className="mt-0.5 text-xs text-slate-400">
          {phase === "recording" ? `${seconds}s / ${config.max_seconds}s` : config.provider === "sarvam" ? "Voice by Sarvam AI" : "Browser voice (add SARVAM_API_KEY for Sarvam)"}
        </p>
      </div>

      <select value={language} onChange={(e) => onLanguage(e.target.value)} aria-label="Language" disabled={phase !== "idle"}
        className="shrink-0 rounded-full border border-brand-600/20 bg-white px-3 py-2 text-sm font-semibold text-brand-800 outline-none">
        {config.languages.map((l) => <option key={l.code} value={l.code}>{l.native}</option>)}
      </select>
      <button type="button" onClick={() => { if (autoSpeak) onStopSpeaking(); onAutoSpeak(!autoSpeak); }}
        aria-label={autoSpeak ? "Turn spoken replies off" : "Turn spoken replies on"} aria-pressed={autoSpeak}
        className={clsx("flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition", autoSpeak ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-400")}>
        {autoSpeak ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
      </button>
    </div>
  );
}
