import { useState } from "react";
import { api } from "../api";
import { Notice, Spinner } from "../ui";
import { PageProps } from "./Translate";

export function Imagine({ options }: PageProps) {
  const [prompt, setPrompt] = useState("A farmer walking through a green rice field at sunrise");
  const [image, setImage] = useState<{ src: string; seconds: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const result = await api.imagine(prompt);
      setImage({ src: `data:image/png;base64,${result.image}`, seconds: (result.latency_ms / 1000).toFixed(1) });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="composer">
        <label htmlFor="prompt">Describe a picture</label>
        <textarea id="prompt" rows={3} maxLength={300} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="composer-foot">
          <span>SD-Turbo</span>
          <button className="primary" onClick={run} disabled={loading || !options || !prompt.trim()}>
            {loading ? "Generating…" : "Generate"}
          </button>
        </div>
      </section>
      {error && <Notice kind="error">{error}</Notice>}
      {loading && <Spinner label="Generating. This can take a minute." />}
      {image && !loading && (
        <figure className="generated">
          <img src={image.src} alt={prompt} />
          <figcaption>Generated in {image.seconds} s.</figcaption>
        </figure>
      )}
    </>
  );
}
