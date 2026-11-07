"""Builds ../docs/report.pdf from results/ using a headless Chromium browser.

Run from the backend folder:  python -m eval.build_report
Set BROWSER_PATH if Microsoft Edge or Chrome is not in its default location.
"""
import html
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGUAGE_NAMES = {"hi": "Hindi", "mr": "Marathi"}
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome",
    "chromium",
]

CSS = """
@page { size: A4; margin: 18mm 17mm; }
body { font: 10.5pt/1.5 "Segoe UI", "Nirmala UI", sans-serif; color: #17171a; }
h1 { font-size: 22pt; margin: 0 0 2pt; letter-spacing: -0.02em; }
h2 { font-size: 13pt; margin: 20pt 0 5pt; padding-bottom: 3pt; border-bottom: 1px solid #ddd; }
h3 { font-size: 10.5pt; margin: 12pt 0 3pt; }
p { margin: 4pt 0 7pt; }
.sub { color: #666; margin-bottom: 14pt; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-size: 9.5pt; }
th { text-align: left; color: #666; font-weight: 600; }
th, td { padding: 4pt 6pt 4pt 0; border-bottom: 1px solid #e6e6e6; vertical-align: top; }
td.n, th.n { text-align: right; white-space: nowrap; }
tr, .flow { break-inside: avoid; }
h2, h3 { break-after: avoid; }
.flow { display: flex; gap: 4pt; margin: 8pt 0; }
.flow div { flex: 1; padding: 5pt 4pt; border: 1px solid #bbb; border-radius: 4pt; font-size: 8.5pt; text-align: center; }
.note { padding: 6pt 9pt; border-left: 3px solid #d59a2e; background: #fbf6ea; font-size: 9.5pt; }
"""


def esc(value):
    return html.escape(str(value))


def table(headers, rows, numeric=()):
    head = "".join(f'<th class="{"n" if i in numeric else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"n" if i in numeric else ""}">{esc(c)}</td>' for i, c in enumerate(row)) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def load(name):
    path = ROOT / "results" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def bleu_section(bleu):
    parts = []
    for lang, rows in bleu["languages"].items():
        parts.append(f"<h3>{LANGUAGE_NAMES[lang]}</h3>")
        parts.append(
            table(
                ["System", "BLEU", "chrF", "Median latency"],
                [[r["system"], r["bleu"], r["chrf"], f'{r["median_latency_ms"]} ms'] for r in rows],
                numeric=(1, 2, 3),
            )
        )
    return "".join(parts)


def failures(bleu):
    rows = []
    for lang, language_rows in bleu["languages"].items():
        row = language_rows[0]
        worst = sorted(range(len(row["per_sentence"])), key=row["per_sentence"].__getitem__)[:3]
        for i in worst:
            rows.append([LANGUAGE_NAMES[lang], bleu["sentences"][i]["en"], row["outputs"][i], row["per_sentence"][i]])
    return table(["Language", "English", "MarianMT output", "BLEU"], rows, numeric=(3,))


def bias_section(bias):
    parts = []
    for lang, rows in bias["languages"].items():
        parts.append(f"<h3>{LANGUAGE_NAMES[lang]}</h3>")
        parts.append(
            table(
                ["System", "Masculine, male-coded", "Masculine, female-coded", "Gap", "“She” respected"],
                [
                    [
                        r["system"],
                        f'{r["male_coded"]["masculine_pct"]}%',
                        f'{r["female_coded"]["masculine_pct"]}%',
                        r["stereotype_gap"],
                        f'{r["she_respected_pct"]}%',
                    ]
                    for r in rows
                ],
                numeric=(1, 2, 3, 4),
            )
        )
        examples = [c for c in rows[0]["she_wrong"]][:2]
        if examples:
            parts.append(table(["Explicit “she”", "MarianMT"], [[c["source"], c["translation"]] for c in examples]))
    return "".join(parts)


def build_html():
    bleu, bias, adequacy = load("bleu"), load("bias"), load("adequacy")
    has_llm = any(r["kind"] == "llm" for rows in bleu["languages"].values() for r in rows)
    pending = (
        ""
        if has_llm
        else '<p class="note">LLM rows are not included yet. Add an API key to .env, rerun the evaluations and rebuild this report.</p>'
    )
    stages = ["Scope", "Data", "Model", "Generate", "Evaluate", "Guard", "Deploy"]
    guard = (
        f'<p>On {adequacy["n_pairs"]} correct and {adequacy["n_pairs"]} shuffled pairs, the meaning check at threshold '
        f'{adequacy["floor"]} caught {adequacy["wrong_caught_pct"]}% of unrelated pairs and passed '
        f'{adequacy["true_pass_pct"]}% of correct ones (AUC {adequacy["auc"]}). That is an easy test. On MarianMT\'s '
        f'{adequacy["real_failures_total"]} lowest-BLEU outputs it flagged only {adequacy["real_failures_flagged"]}, '
        "so it stops unrelated text but misses translations that are wrong yet on topic, such as a literal idiom. "
        "Not every low-BLEU output is wrong, but this guardrail must not be treated as an accuracy check.</p>'
        if adequacy
        else ""
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Lingo report</title><style>{CSS}</style></head><body>
<h1>Lingo</h1>
<p class="sub">P19 · Encoder–Decoder Translator, English to Hindi and Marathi</p>
{pending}

<h2>1. Goal</h2>
<p>Translate text and image captions, and compare a seq2seq model with an LLM on quality, speed and fairness.</p>

<h2>2. System</h2>
<p>A React frontend on Vercel calls a FastAPI backend on Render, which holds the keys, applies the guardrails and calls Groq or Gemini. PyTorch with one MarianMT model measured 808 MB of RAM against Render's free 512 MB, so the PyTorch models run on a free Hugging Face Space, as the brief allows for heavy models.</p>
<div class="flow">{"".join(f"<div>{s}</div>" for s in stages)}</div>

<h2>3. Layer coverage</h2>
{table(["Layer", "How it is met"], [
    ["I Foundations", "Lifecycle diagram above. Both translators are generative models of P(target | source); the meaning check is discriminative in spirit. Zero-shot and few-shot prompts are compared. Beam search probabilities give the probability view."],
    ["II GANs and LLMs", "A transformer LLM is central, adapted by prompt-based learning rather than fine-tuning. Cross-attention is visualised live as the attention explanation."],
    ["III GPT, BERT, multimodal", "A GPT-style LLM, MiniLM as the BERT-family model, and image (BLIP, SD-Turbo) and audio (gTTS) modalities."],
    ["IV Tools and generation", "Python and PyTorch throughout, with image generation by SD-Turbo."],
    ["V Responsible AI", "Measured gender bias test, input and output guardrails, licence and IP note, and a model card."],
])}

<h2>4. Tasks</h2>
<p><b>U1.</b> Four registers (neutral, formal, casual, for children), each with zero-shot and few-shot prompts. Source text sits in delimiters and is treated as data.</p>
<p><b>U2.</b> MarianMT and the LLM run side by side. Marathi uses opus-mt-en-inc, because opus-mt-en-mr invented content in testing.</p>
<p><b>U3.</b> BLIP captions an upload, then both models translate the caption.</p>
<p><b>U4.</b> Any translation can be spoken with gTTS.</p>
<p><b>U5.</b> Gender bias is measured below and can be probed live in the Bias lab.</p>

<h2>5. BLEU on 20 sentences</h2>
<p>Corpus BLEU and chrF, with Devanagari punctuation normalised first. BLEU is low in absolute terms because Hindi and Marathi word order is flexible and each sentence has one reference.</p>
{bleu_section(bleu)}

<h2>6. Failure cases</h2>
<p>The three lowest-scoring MarianMT sentences per language.</p>
{failures(bleu)}

<h2>7. Bias examples</h2>
<p>Sixty sentences with no stated gender, half with male-coded jobs and half with female-coded jobs, plus twenty with an explicit “she”. The rule-based detector reads the verb form. Translations with no gendered verb count as neutral.</p>
{bias_section(bias)}

<h2>8. Guardrails</h2>
<p>Input length and harmful-request filters, delimiting against prompt injection, Devanagari output validation, per-client rate limiting, a gender notice, and a BERT-family meaning check.</p>
{guard}

<h2>9. Limitations</h2>
<p>Twenty sentences with one reference each is a small test, so small differences are not meaningful. The references were drafted with AI assistance and should be reviewed by a fluent speaker. The keyword filter is not full moderation, and the gender detector covers common verb forms only.</p>

<h2>10. Licence and IP</h2>
<p>MarianMT and MiniLM are Apache 2.0, and BLIP is BSD 3-Clause. SD-Turbo's community licence limits commercial use. LLM use follows provider terms. gTTS calls an unofficial Google endpoint. See MODEL_CARD.md.</p>
</body></html>"""


def main():
    docs = ROOT.parent / "docs"
    source = docs / "report.html"
    source.write_text(build_html(), encoding="utf-8")
    browser = os.getenv("BROWSER_PATH") or next(b for b in BROWSERS if Path(b).exists() or shutil.which(b))
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={ROOT / '.browser-profile'}",
            f"--print-to-pdf={docs / 'report.pdf'}",
            source.as_uri(),
        ],
        check=True,
        timeout=120,
    )
    shutil.rmtree(ROOT / ".browser-profile", ignore_errors=True)
    print("Wrote", docs / "report.pdf")


if __name__ == "__main__":
    main()
