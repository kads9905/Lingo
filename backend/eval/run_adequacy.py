"""Calibrates the BERT-family meaning check used as the hallucination guardrail.

Run from the backend folder:  python -m eval.run_adequacy

Shuffled pairs give each English sentence another sentence's reference, an easy
test. Real pairs score MarianMT's five worst outputs per language, which shows
what the check misses when a translation is wrong but on topic.
"""
import json
from pathlib import Path

from app.guardrails import ADEQUACY_FLOOR
from ml_worker import engine

ROOT = Path(__file__).resolve().parent.parent
SENTENCES = json.loads((ROOT / "data" / "eval_sentences.json").read_text(encoding="utf-8"))


def real_failures():
    bleu = json.loads((ROOT / "results" / "bleu.json").read_text(encoding="utf-8"))
    failures = []
    for language_rows in bleu["languages"].values():
        row = language_rows[0]
        for i in sorted(range(len(SENTENCES)), key=row["per_sentence"].__getitem__)[:5]:
            source, output = SENTENCES[i]["en"], row["outputs"][i]
            score = engine.adequacy(source, output)["score"]
            failures.append({"source": source, "output": output, "score": score, "flagged": score < ADEQUACY_FLOOR})
    return failures


def main():
    correct, wrong = [], []
    for lang in ("hi", "mr"):
        for i, sentence in enumerate(SENTENCES):
            other = SENTENCES[(i + 7) % len(SENTENCES)]
            correct.append(engine.adequacy(sentence["en"], sentence[lang])["score"])
            wrong.append(engine.adequacy(sentence["en"], other[lang])["score"])

    candidates = sorted(set(correct + wrong))
    best = max(candidates, key=lambda t: sum(c >= t for c in correct) + sum(w < t for w in wrong))
    wins = sum(c > w for c in correct for w in wrong) + 0.5 * sum(c == w for c in correct for w in wrong)
    failures = real_failures()
    report = {
        "n_pairs": len(correct),
        "mean_correct": round(sum(correct) / len(correct), 3),
        "mean_wrong": round(sum(wrong) / len(wrong), 3),
        "lowest_correct": min(correct),
        "highest_wrong": max(wrong),
        "floor": ADEQUACY_FLOOR,
        "true_pass_pct": round(100 * sum(c >= ADEQUACY_FLOOR for c in correct) / len(correct), 1),
        "wrong_caught_pct": round(100 * sum(w < ADEQUACY_FLOOR for w in wrong) / len(wrong), 1),
        "auc": round(wins / (len(correct) * len(wrong)), 3),
        "real_failures_flagged": sum(f["flagged"] for f in failures),
        "real_failures_total": len(failures),
        "real_failures": failures,
        "best_threshold": best,
    }
    print({k: v for k, v in report.items() if k != "real_failures"})
    for failure in failures:
        print(failure["score"], failure["flagged"], failure["source"], "=>", failure["output"])
    (ROOT / "results" / "adequacy.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
