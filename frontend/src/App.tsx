import { useEffect, useState } from "react";
import { api, Health, Options } from "./api";
import { About } from "./pages/About";
import { BiasLab } from "./pages/BiasLab";
import { Imagine } from "./pages/Imagine";
import { Photo } from "./pages/Photo";
import { Results } from "./pages/Results";
import { Translate } from "./pages/Translate";
import { Settings } from "./ui";

const TABS = [
  { id: "translate", label: "Translate" },
  { id: "photo", label: "Photo" },
  { id: "imagine", label: "Imagine" },
  { id: "bias", label: "Bias lab" },
  { id: "results", label: "Results" },
  { id: "about", label: "About" },
] as const;

type Tab = (typeof TABS)[number]["id"];
const WAKE_POLL_MS = 4000;
const SLOW_START_MS = 2500;

export default function App() {
  const [tab, setTab] = useState<Tab>("translate");
  const [health, setHealth] = useState<Health | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [slowStart, setSlowStart] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    lang: "hi",
    register: "neutral",
    technique: "few_shot",
    provider: "",
  });

  // Free hosts sleep when idle, so keep polling until both backend and models answer.
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const next = await api.health();
        if (cancelled) return;
        setHealth(next);
        if (next.models_ready) {
          setOptions(await api.options());
          return;
        }
      } catch {
        // Still waking up.
      }
      if (!cancelled) setTimeout(poll, WAKE_POLL_MS);
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setSlowStart(true), SLOW_START_MS);
    return () => clearTimeout(timer);
  }, []);

  const ready = health?.models_ready && options;
  const shared = { settings, setSettings, options, providers: health?.providers ?? [] };

  return (
    <div className="shell">
      <header className="masthead">
        <span className="brand">Lingo</span>
        <nav className="tabs" aria-label="Sections">
          {TABS.map(({ id, label }) => (
            <button key={id} className={tab === id ? "active" : ""} aria-current={tab === id} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
        <span className={`status ${ready ? "up" : "waking"}`}>
          <span>{ready ? "Ready" : "Starting"}</span>
        </span>
      </header>

      <main>
        {!ready && slowStart && <p className="wake-note">Starting up. The first visit can take a minute or two.</p>}
        {tab === "translate" && <Translate {...shared} />}
        {tab === "photo" && <Photo {...shared} />}
        {tab === "imagine" && <Imagine {...shared} />}
        {tab === "bias" && <BiasLab settings={settings} options={options} />}
        {tab === "results" && <Results />}
        {tab === "about" && <About />}
      </main>

      <footer className="colophon">Machine translation can be wrong. Check anything important.</footer>
    </div>
  );
}
