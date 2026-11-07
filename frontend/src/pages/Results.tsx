import { useEffect, useState } from "react";
import { api, BiasRow, BleuRow, Lang, Results as Data } from "../api";
import { Notice, Segmented, Select, Spinner } from "../ui";

function Bars({ rows }: { rows: BleuRow[] }) {
  const peak = Math.max(...rows.map((row) => row.bleu), 1);
  return (
    <div className="bars">
      {rows.map((row) => (
        <div className={`bar-row ${row.kind}`} key={row.system}>
          <span className="bar-label">{row.system}</span>
          <span className="bar-track">
            <i style={{ width: `${(row.bleu / peak) * 100}%` }} />
          </span>
          <span className="num">{row.bleu.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

function BleuSection({ rows, sentences, lang }: { rows: BleuRow[]; sentences: Record<string, string>[]; lang: Lang }) {
  const [open, setOpen] = useState(0);
  const worst = rows[0].per_sentence.indexOf(Math.min(...rows[0].per_sentence));
  const sentence = sentences[open];
  return (
    <section className="panel">
      <h2>Translation quality on 20 sentences</h2>
      <p>Higher is better. Compare systems within this table, not with published BLEU figures.</p>
      <Bars rows={rows} />
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>System</th>
              <th className="num">BLEU</th>
              <th className="num">chrF</th>
              <th className="num">Median latency</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.system}>
                <td>{row.system}</td>
                <td className="num">{row.bleu.toFixed(2)}</td>
                <td className="num">{row.chrf.toFixed(2)}</td>
                <td className="num">{row.median_latency_ms} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Sentence by sentence</h3>
      <div className="stepper">
        <Select
          label="Sentence"
          value={String(open)}
          options={sentences.map((s, i) => ({ value: String(i), label: `${i + 1}. ${s.en}` }))}
          onChange={(value) => setOpen(Number(value))}
        />
        <button className="secondary" onClick={() => setOpen(worst)}>
          Worst for MarianMT
        </button>
      </div>
      <dl className="sentence-view">
        <div>
          <dt>Reference</dt>
          <dd className="devanagari">{sentence[lang]}</dd>
        </div>
        {rows.map((row) => (
          <div key={row.system}>
            <dt>
              {row.system} <span className="num">· {row.per_sentence[open]}</span>
            </dt>
            <dd className="devanagari">{row.outputs[open]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function BiasSection({ rows }: { rows: BiasRow[] }) {
  const examples = rows[0].records.filter((_, i) => i % 13 === 0).slice(0, 5);
  return (
    <section className="panel">
      <h2>Gender bias in professions</h2>
      <p>
        Share of ungendered sentences rendered masculine. A smaller gap is fairer.
      </p>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>System</th>
              <th className="num">Male-coded jobs</th>
              <th className="num">Female-coded jobs</th>
              <th className="num">Gap (points)</th>
              <th className="num">“She” respected</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.system}>
                <td>{row.system}</td>
                <td className="num">{row.male_coded.masculine_pct}%</td>
                <td className="num">{row.female_coded.masculine_pct}%</td>
                <td className="num">{row.stereotype_gap}</td>
                <td className="num">{row.she_respected_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Examples from MarianMT</h3>
      <ul className="examples-list">
        {examples.map((record) => (
          <li key={record.source}>
            <span>{record.source}</span>
            <span className="devanagari">{record.translation}</span>
            <span className={`pill ${record.gender}`}>{record.gender}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Results() {
  const [data, setData] = useState<Data | null>(null);
  const [lang, setLang] = useState<Lang>("hi");
  const [error, setError] = useState("");

  useEffect(() => {
    api.results().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <Notice kind="error">{error}</Notice>;
  if (!data) return <Spinner label="Loading the evaluation results." />;

  return (
    <>
      <div className="results-head">
        <h2>Evaluation</h2>
        <Segmented
          label="Target language"
          value={lang}
          options={[
            { value: "hi", label: "हिन्दी" },
            { value: "mr", label: "मराठी" },
          ]}
          onChange={setLang}
        />
      </div>
      {data.bleu && <BleuSection key={lang} rows={data.bleu.languages[lang]} sentences={data.bleu.sentences} lang={lang} />}
      {data.bias && <BiasSection rows={data.bias.languages[lang]} />}
      {data.adequacy && (
        <section className="panel">
          <h2>Meaning-match guardrail</h2>
          <p>
            MiniLM, a BERT-family model, compares the English with its translation. It reliably catches unrelated text,
            but it misses translations that are wrong yet on topic.
          </p>
          <div className="stats">
            <div>
              <strong>{data.adequacy.wrong_caught_pct}%</strong>
              <span>unrelated pairs caught</span>
            </div>
            <div>
              <strong>{data.adequacy.true_pass_pct}%</strong>
              <span>correct pairs passed</span>
            </div>
            <div>
              <strong>
                {data.adequacy.real_failures_flagged} of {data.adequacy.real_failures_total}
              </strong>
              <span>lowest-BLEU outputs flagged</span>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
