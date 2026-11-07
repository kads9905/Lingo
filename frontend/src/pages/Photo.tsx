import { useState } from "react";
import { api, CaptionResult } from "../api";
import { Comparison, Notice, SettingsBar, Spinner } from "../ui";
import { PageProps } from "./Translate";

export function Photo({ settings, setSettings, options, providers }: PageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<CaptionResult | null>(null);
  const [resultLang, setResultLang] = useState(settings.lang);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function choose(next: File | undefined) {
    if (!next) return;
    setFile(next);
    setPreview(URL.createObjectURL(next));
    setResult(null);
    setError("");
  }

  async function run() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const { lang, register, technique, provider } = settings;
      const fields: Record<string, string> = { lang, tone: register, technique };
      if (provider) fields.provider = provider;
      setResult(await api.caption(file, fields));
      setResultLang(lang);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="composer">
        <SettingsBar settings={settings} options={options} providers={providers} onChange={setSettings} />
        <label
          className={`dropzone ${preview ? "filled" : ""}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            choose(e.dataTransfer.files[0]);
          }}
        >
          <input type="file" accept="image/*" onChange={(e) => choose(e.target.files?.[0])} />
          {preview ? (
            <img src={preview} alt="Your upload" />
          ) : (
            <span>
              <strong>Choose a photo</strong> or drop it here
              <small>JPG or PNG, up to 6 MB</small>
            </span>
          )}
        </label>
        <div className="composer-foot">
          <span>BLIP captions it, then both models translate.</span>
          <button className="primary" onClick={run} disabled={loading || !file || !options}>
            {loading ? "Working…" : "Translate photo"}
          </button>
        </div>
      </section>

      {error && <Notice kind="error">{error}</Notice>}
      {loading && <Spinner label="Reading the photo" />}
      {result && !loading && (
        <>
          <section className="panel caption-result">
            <span className="tag">Caption · {(result.caption_ms / 1000).toFixed(1)} s</span>
            <p>{result.caption}</p>
          </section>
          <Comparison result={result} lang={resultLang} />
        </>
      )}
    </>
  );
}
