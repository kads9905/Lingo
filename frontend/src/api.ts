const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
// Long enough for a sleeping model worker to wake and load its first model.
const TIMEOUT_MS = 300_000;

export type Lang = "hi" | "mr";

export interface Candidate {
  translation?: string;
  latency_ms?: number;
  adequacy?: number;
  warnings?: string[];
  error?: string;
  model?: string;
  provider?: string;
}

export interface TranslateResult {
  warnings?: string[];
  seq2seq: Candidate;
  llm: Candidate;
}

export interface CaptionResult extends TranslateResult {
  caption: string;
  caption_ms: number;
}

export interface Inspection {
  sentence: string;
  alternatives: { text: string; log_prob: number; share: number }[];
  attention: { source: string[]; target: string[]; weights: number[][] };
}

export interface Health {
  status: string;
  models_ready: boolean;
  providers: { id: string; model: string }[];
}

export interface Options {
  languages: Record<Lang, string>;
  registers: Record<string, { label: string; hint: string }>;
  techniques: Record<string, string>;
  professions: { male_coded: string[]; female_coded: string[] };
}

export interface BiasGuess {
  translation?: string;
  gender?: string;
  error?: string;
}

export interface Probe {
  sentence: string;
  seq2seq: BiasGuess;
  llm: BiasGuess;
  llm_fair: BiasGuess;
}

export interface BleuRow {
  system: string;
  kind: string;
  bleu: number;
  chrf: number;
  median_latency_ms: number;
  per_sentence: number[];
  outputs: string[];
}

export interface BiasGroup {
  n: number;
  masculine: number;
  feminine: number;
  neutral: number;
  masculine_pct: number;
}

export interface BiasRow {
  system: string;
  kind: string;
  male_coded: BiasGroup;
  female_coded: BiasGroup;
  stereotype_gap: number;
  she_respected_pct: number;
  she_wrong: { source: string; translation: string }[];
  records: { group: string; profession: string; source: string; translation: string; gender: string }[];
}

export interface Results {
  bleu: { sentences: Record<string, string>[]; languages: Record<Lang, BleuRow[]> } | null;
  bias: { languages: Record<Lang, BiasRow[]> } | null;
  adequacy: {
    n_pairs: number;
    mean_correct: number;
    mean_wrong: number;
    real_failures_flagged: number;
    real_failures_total: number;
    true_pass_pct: number;
    wrong_caught_pct: number;
    auc: number;
  } | null;
}

async function unwrap<T>(response: Response): Promise<T> {
  if (response.ok) return response.json();
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Something went wrong. Please try again.";
  throw new Error(detail);
}

async function request(path: string, init?: RequestInit) {
  try {
    return await fetch(BASE + path, { ...init, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch {
    throw new Error("Could not reach the server. Check your connection and try again.");
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return unwrap<T>(response);
}

const get = async <T,>(path: string) => unwrap<T>(await request(path));

export const api = {
  health: () => get<Health>("/api/health"),
  options: () => get<Options>("/api/options"),
  results: () => get<Results>("/api/results"),
  translate: (body: object) => post<TranslateResult>("/api/translate", body),
  inspect: (text: string, lang: Lang) => post<Inspection>("/api/inspect", { text, lang }),
  imagine: (prompt: string) => post<{ image: string; latency_ms: number }>("/api/imagine", { prompt }),
  probe: (profession: string, lang: Lang, provider?: string) =>
    post<Probe>("/api/bias/probe", { profession, lang, provider }),
  caption: async (image: File, fields: Record<string, string>) => {
    const form = new FormData();
    form.append("image", image);
    Object.entries(fields).forEach(([key, value]) => form.append(key, value));
    return unwrap<CaptionResult>(await request("/api/caption", { method: "POST", body: form }));
  },
  speak: async (text: string, lang: Lang) => {
    const response = await request("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    });
    if (!response.ok) throw new Error("Speech is unavailable right now.");
    return URL.createObjectURL(await response.blob());
  },
};
