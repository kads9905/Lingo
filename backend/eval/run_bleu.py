"""BLEU and chrF on the 20 reference sentences: MarianMT against the LLM.

Run from the backend folder:  python -m eval.run_bleu
LLM rows appear only when GROQ_API_KEY or GEMINI_API_KEY is set in .env.
"""
import json
import re
import time
from pathlib import Path

import sacrebleu

from app import llm  # noqa: F401  (app.main loads .env on import)
from app import main as _env  # noqa: F401
from app.prompts import LANGUAGES, build_messages
from ml_worker import engine

ROOT = Path(__file__).resolve().parent.parent
SENTENCES = json.loads((ROOT / "data" / "eval_sentences.json").read_text(encoding="utf-8"))
REJECTED_MARATHI = ("Helsinki-NLP/opus-mt-en-mr", "")
LLM_PAUSE_SECONDS = 2.5


def normalise(text):
    """sacrebleu's default tokeniser does not split the Devanagari danda from words."""
    text = re.sub(r"([।,.?!;:\"'()])", r" \1 ", text.replace("‍", "").replace("‌", ""))
    return " ".join(text.replace("।", ".").split())


def score(hypotheses, references):
    hypotheses = [normalise(h) for h in hypotheses]
    references = [normalise(r) for r in references]
    per_sentence = [
        round(sacrebleu.sentence_bleu(h, [r], tokenize="none", smooth_method="exp").score, 1)
        for h, r in zip(hypotheses, references)
    ]
    return {
        "bleu": round(sacrebleu.corpus_bleu(hypotheses, [references], tokenize="none").score, 2),
        "chrf": round(sacrebleu.corpus_chrf(hypotheses, [references]).score, 2),
        "per_sentence": per_sentence,
    }


def run_marian(lang, model_name=None, prefix=None):
    outputs = [engine.translate(s["en"], lang, model_name, prefix) for s in SENTENCES]
    return [o["translation"] for o in outputs], [o["latency_ms"] for o in outputs]


def run_llm(lang, technique):
    outputs = []
    for sentence in SENTENCES:
        outputs.append(llm.complete(build_messages(sentence["en"], lang, technique=technique), retries=4))
        time.sleep(LLM_PAUSE_SECONDS)
    return [o["translation"] for o in outputs], [o["latency_ms"] for o in outputs], outputs[0]["model"]


def row(system, kind, hypotheses, latencies, references):
    return {
        "system": system,
        "kind": kind,
        **score(hypotheses, references),
        "median_latency_ms": sorted(latencies)[len(latencies) // 2],
        "outputs": hypotheses,
    }


def main():
    report = {"sentences": SENTENCES, "languages": {}}
    for lang in LANGUAGES:
        references = [s[lang] for s in SENTENCES]
        name = engine.MARIAN_MODELS[lang][0].split("/")[1]
        rows = [row(f"MarianMT ({name})", "seq2seq", *run_marian(lang), references)]
        if lang == "mr":
            rows.append(
                row("MarianMT (opus-mt-en-mr, rejected)", "rejected", *run_marian(lang, *REJECTED_MARATHI), references)
            )
        if llm.available():
            for technique, label in (("zero_shot", "zero-shot"), ("few_shot", "few-shot")):
                hypotheses, latencies, model = run_llm(lang, technique)
                rows.append(row(f"{model} ({label})", "llm", hypotheses, latencies, references))
        report["languages"][lang] = rows
        for r in rows:
            print(lang, r["system"], "BLEU", r["bleu"], "chrF", r["chrf"], "median ms", r["median_latency_ms"])

    path = ROOT / "results" / "bleu.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
