import { ReactNode, useEffect, useRef, useState } from "react";
import { api, Candidate, Lang, Options, TranslateResult } from "./api";

export interface Settings {
  lang: Lang;
  register: string;
  technique: string;
  provider: string;
}

export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string; title?: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="field">
      <div className="segmented" role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={value === option.value}
            title={option.title}
            className={value === option.value ? "active" : ""}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <span className="select">
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <path d="M2 3.5 5 6.5 8 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

export function SettingsBar({
  settings,
  options,
  providers,
  onChange,
}: {
  settings: Settings;
  options: Options | null;
  providers: { id: string; model: string }[];
  onChange: (settings: Settings) => void;
}) {
  const set = (patch: Partial<Settings>) => onChange({ ...settings, ...patch });
  return (
    <div className="settings">
      <Segmented
        label="Translate into"
        value={settings.lang}
        options={[
          { value: "hi", label: "हिन्दी" },
          { value: "mr", label: "मराठी" },
        ]}
        onChange={(lang) => set({ lang })}
      />
      <Select
        label="Tone"
        value={settings.register}
        options={Object.entries(options?.registers ?? {}).map(([value, r]) => ({ value, label: r.label }))}
        onChange={(register) => set({ register })}
      />
      <Select
        label="Prompt technique"
        value={settings.technique}
        options={Object.entries(options?.techniques ?? {}).map(([value, label]) => ({ value, label }))}
        onChange={(technique) => set({ technique })}
      />
      {providers.length > 1 && (
        <Select
          label="LLM provider"
          value={settings.provider || providers[0].id}
          options={providers.map((p) => ({ value: p.id, label: p.id === "groq" ? "Groq" : "Gemini" }))}
          onChange={(provider) => set({ provider })}
        />
      )}
    </div>
  );
}

export function Notice({ kind = "warn", children }: { kind?: "warn" | "error"; children: ReactNode }) {
  return (
    <p className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

function SpeakButton({ text, lang }: { text: string; lang: Lang }) {
  const [state, setState] = useState<"idle" | "loading" | "failed">("idle");
  const [src, setSrc] = useState<string | null>(null);
  const audio = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    setSrc(null);
    setState("idle");
  }, [text, lang]);

  useEffect(() => {
    if (src) audio.current?.play().catch(() => undefined);
  }, [src]);

  async function speak() {
    if (src) {
      audio.current?.play();
      return;
    }
    setState("loading");
    try {
      setSrc(await api.speak(text, lang));
      setState("idle");
    } catch {
      setState("failed");
    }
  }

  return (
    <>
      <button type="button" className="ghost" onClick={speak} disabled={state === "loading"}>
        {state === "loading" ? "Loading…" : state === "failed" ? "Retry audio" : "Listen"}
      </button>
      {src && <audio ref={audio} src={src} />}
    </>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="ghost"
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function CandidateCard({
  eyebrow,
  name,
  candidate,
  lang,
}: {
  eyebrow: string;
  name: string;
  candidate: Candidate;
  lang: Lang;
}) {
  return (
    <article className="candidate">
      <header>
        <h3>{candidate.model ?? name}</h3>
        <span className="tag">{eyebrow}</span>
      </header>
      {candidate.translation ? (
        <>
          <p className="devanagari translation" lang={lang}>
            {candidate.translation}
          </p>
          {candidate.warnings?.map((warning) => <Notice key={warning}>{warning}</Notice>)}
          <footer>
            <span className="metrics">
              <span title="Meaning match between the English and this translation">
                Match <b>{candidate.adequacy?.toFixed(2)}</b>
              </span>
              <span>
                <b>{((candidate.latency_ms ?? 0) / 1000).toFixed(2)}</b> s
              </span>
            </span>
            <div className="actions">
              <CopyButton text={candidate.translation} />
              <SpeakButton text={candidate.translation} lang={lang} />
            </div>
          </footer>
        </>
      ) : (
        <Notice kind="error">{candidate.error}</Notice>
      )}
    </article>
  );
}

export function Comparison({ result, lang }: { result: TranslateResult; lang: Lang }) {
  return (
    <section className="comparison" aria-live="polite">
      <CandidateCard eyebrow="Encoder–decoder" name="MarianMT" candidate={result.seq2seq} lang={lang} />
      <CandidateCard eyebrow="LLM" name="LLM" candidate={result.llm} lang={lang} />
    </section>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="spinner" role="status">
      <span />
      {label}
    </div>
  );
}
