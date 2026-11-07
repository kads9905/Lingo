const STAGES = [
  ["Scope", "English to Hindi and Marathi, with tone control"],
  ["Data", "20 reference sentences, 80 bias prompts"],
  ["Model", "MarianMT, Groq or Gemini LLM, BLIP, MiniLM, SD-Turbo"],
  ["Generate", "Beam search, prompted LLM, one-step diffusion"],
  ["Evaluate", "BLEU, chrF, latency, gender gap"],
  ["Guard", "Input filters, output checks, meaning match"],
  ["Deploy", "Vercel, Render and a model worker"],
];

const MODELS = [
  ["MarianMT (opus-mt-en-hi, en-inc)", "Encoder–decoder translator", "Apache 2.0"],
  ["gpt-oss-120b on Groq, or Gemini", "LLM translator with tone prompts", "Apache 2.0, provider terms"],
  ["BLIP base", "Image captioning", "BSD 3-Clause"],
  ["MiniLM multilingual", "BERT-family meaning check", "Apache 2.0"],
  ["SD-Turbo", "Image generation", "Stability AI community licence"],
  ["gTTS", "Speech via Google Translate's voice", "MIT library; unofficial service"],
];

export function About() {
  return (
    <>
      <section className="panel">
        <h2>How it was built</h2>
        <ol className="lifecycle">
          {STAGES.map(([name, detail]) => (
            <li key={name}>
              <strong>{name}</strong>
              <span>{detail}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="panel prose">
        <h2>Two ways of modelling translation</h2>
        <p>
          Both translators are generative: they model the probability of a target sentence given the source. MarianMT
          learned that distribution only from aligned sentence pairs, so it is fast and predictable but cannot be told
          what tone to use. The LLM was trained on general text and is steered by prompts. The meaning-match check is
          discriminative in spirit: it does not create text, it only judges whether two sentences agree.
        </p>
      </section>
      <section className="panel">
        <h2>Models and licences</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Model</th>
                <th>Role</th>
                <th>Licence</th>
              </tr>
            </thead>
            <tbody>
              {MODELS.map(([model, role, licence]) => (
                <tr key={model}>
                  <td>{model}</td>
                  <td>{role}</td>
                  <td>{licence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel prose">
        <h2>Limits</h2>
        <p>
          Do not rely on this tool for medical, legal or official text. Machine translation can read fluently and still
          be wrong, and it can assign a gender the English never stated.
        </p>
      </section>
    </>
  );
}
