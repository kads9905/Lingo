import { useState } from "react";
import { api, Inspection, Options, TranslateResult } from "../api";
import { Comparison, Notice, Settings, SettingsBar, Spinner } from "../ui";

export interface PageProps {
  settings: Settings;
  setSettings: (settings: Settings) => void;
  options: Options | null;
  providers: { id: string; model: string }[];
}

const EXAMPLES = [
  "Heavy rain has caused floods in several districts.",
  "The engineer finished the work and went home.",
  "It is raining cats and dogs outside.",
  "Thank you very much for your kindness.",
];

function AttentionMap({ data }: { data: Inspection["attention"] }) {
  const clean = (token: string) => token.replace("▁", "");
  const peak = Math.max(...data.weights.flat());
  return (
    <div className="attention" role="img" aria-label="Cross-attention between English and translated tokens">
      <table>
        <thead>
          <tr>
            <th />
            {data.source.map((token, i) => (
              <th key={i} scope="col">
                <span>{clean(token)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.weights.map((row, i) => (
            <tr key={i}>
              <th scope="row" className="devanagari">
                {clean(data.target[i])}
              </th>
              {row.map((weight, j) => (
                <td
                  key={j}
                  title={weight.toFixed(3)}
                  style={{ background: `color-mix(in srgb, var(--accent) ${Math.round((100 * weight) / peak)}%, var(--raised))` }}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Inside({ text, settings }: { text: string; settings: Settings }) {
  const [data, setData] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function open() {
    setLoading(true);
    setError("");
    try {
      setData(await api.inspect(text, settings.lang));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel inside">
      <div className="panel-head">
        <div>
          <h2>Model internals</h2>
          <p>What the encoder–decoder attended to, and what it nearly said.</p>
        </div>
        {!data && (
          <button className="secondary" onClick={open} disabled={loading}>
            {loading ? "Loading…" : "Show"}
          </button>
        )}
      </div>
      {error && <Notice kind="error">{error}</Notice>}
      {data && (
        <div className="inside-grid">
          <div>
            <h3>Cross-attention</h3>
            <p className="caption">Brighter cells mean more attention on that English token.</p>
            <AttentionMap data={data.attention} />
          </div>
          <div>
            <h3>Beam search</h3>
            <p className="caption">Relative probability of the five finished beams.</p>
            <ol className="beams">
              {data.alternatives.map((beam, i) => (
                <li key={i}>
                  <span className="devanagari">{beam.text}</span>
                  <span className="beam-bar">
                    <i style={{ width: `${beam.share * 100}%` }} />
                  </span>
                  <span className="num">{(beam.share * 100).toFixed(0)}%</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </section>
  );
}

export function Translate({ settings, setSettings, options, providers }: PageProps) {
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [result, setResult] = useState<TranslateResult | null>(null);
  const [resultLang, setResultLang] = useState(settings.lang);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run(source = text) {
    setLoading(true);
    setError("");
    try {
      const { lang, register, technique, provider } = settings;
      setResult(await api.translate({ text: source, lang, tone: register, technique, provider: provider || null }));
      setSubmitted(source);
      setResultLang(lang);
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {!result && !loading && (
        <div className="hero">
          <h1>English to Hindi and Marathi.</h1>
          <p>Two translators, side by side, in the tone you choose.</p>
        </div>
      )}
      <section className="composer">
        <SettingsBar settings={settings} options={options} providers={providers} onChange={setSettings} />
        <textarea
          id="source"
          aria-label="English text"
          rows={4}
          maxLength={600}
          value={text}
          placeholder="Enter English text"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run();
          }}
        />
        <div className="composer-foot">
          <span className="num">{text.length} / 600</span>
          <button className="primary" onClick={() => run()} disabled={loading || !options || !text.trim()}>
            {loading ? "Translating…" : "Translate"}
          </button>
        </div>
      </section>

      {!result && !loading && (
        <div className="examples">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              disabled={!options}
              onClick={() => {
                setText(example);
                run(example);
              }}
            >
              {example}
            </button>
          ))}
        </div>
      )}
      {error && <Notice kind="error">{error}</Notice>}
      {loading && <Spinner label="Translating" />}
      {result && !loading && (
        <>
          {result.warnings?.map((warning) => <Notice key={warning}>{warning}</Notice>)}
          <Comparison result={result} lang={resultLang} />
          <Inside key={`${submitted}-${resultLang}`} text={submitted} settings={{ ...settings, lang: resultLang }} />
        </>
      )}
    </>
  );
}
