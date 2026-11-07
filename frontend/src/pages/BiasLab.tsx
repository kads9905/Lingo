import { useState } from "react";
import { api, BiasGuess, Options, Probe } from "../api";
import { Notice, Settings, Spinner } from "../ui";

function Guess({ label, guess }: { label: string; guess: BiasGuess }) {
  return (
    <div className="guess">
      <span className="tag">{label}</span>
      {guess.translation ? (
        <>
          <p className="devanagari">{guess.translation}</p>
          <span className={`pill ${guess.gender}`}>{guess.gender}</span>
        </>
      ) : (
        <p className="muted">{guess.error}</p>
      )}
    </div>
  );
}

export function BiasLab({ settings, options }: { settings: Settings; options: Options | null }) {
  const [profession, setProfession] = useState("");
  const [probe, setProbe] = useState<Probe | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run(value: string) {
    setProfession(value);
    setLoading(true);
    setError("");
    try {
      setProbe(await api.probe(value, settings.lang, settings.provider || undefined));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const groups = [
    ["Often assumed male", options?.professions.male_coded ?? []],
    ["Often assumed female", options?.professions.female_coded ?? []],
  ] as const;

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Does the model guess a gender?</h2>
            <p>English says “the nurse went home” without a gender. Hindi and Marathi verbs must pick one.</p>
          </div>
        </div>
        {groups.map(([title, list]) => (
          <div className="chip-group" key={title}>
            <span className="field-label">{title}</span>
            <div className="chips">
              {list.map((item) => (
                <button key={item} className={profession === item ? "active" : ""} onClick={() => run(item)} disabled={loading}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        ))}
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (profession.trim().length > 1) run(profession.trim());
          }}
        >
          <input
            aria-label="Your own profession"
            placeholder="Or type another profession"
            value={profession}
            maxLength={40}
            onChange={(e) => setProfession(e.target.value)}
          />
          <button className="secondary" disabled={loading}>
            Test
          </button>
        </form>
      </section>
      {error && <Notice kind="error">{error}</Notice>}
      {loading && <Spinner label="Testing" />}
      {probe && !loading && (
        <section className="panel">
          <p className="probe-source">{probe.sentence}</p>
          <div className="guesses">
            <Guess label="MarianMT" guess={probe.seq2seq} />
            <Guess label="LLM" guess={probe.llm} />
            <Guess label="LLM + gender-fair prompt" guess={probe.llm_fair} />
          </div>
        </section>
      )}
    </>
  );
}
