"""U5: gender bias in translated professions.

Run from the backend folder:  python -m eval.run_bias

Measures how often an ungendered profession is rendered masculine, split by
stereotype, then whether an explicit "she" is respected.
"""
import json
import time
from pathlib import Path

from app import bias, llm
from app import main as _env  # noqa: F401  (loads .env)
from app.prompts import LANGUAGES, build_messages
from ml_worker import engine

ROOT = Path(__file__).resolve().parent.parent
LLM_PAUSE_SECONDS = 2.5


def marian(text, lang):
    return engine.translate(text, lang)["translation"]


def llm_translator(gender_fair):
    def translate(text, lang):
        time.sleep(LLM_PAUSE_SECONDS)
        messages = build_messages(text, lang, gender_fair=gender_fair)
        try:
            return llm.complete(messages, retries=4)["translation"]
        except llm.LLMError as error:
            print("Skipped:", text, error)
            return None

    return translate


def rates(records):
    total = len(records) or 1
    counts = {g: sum(r["gender"] == g for r in records) for g in ("masculine", "feminine", "neutral")}
    return {"n": len(records), **counts, "masculine_pct": round(100 * counts["masculine"] / total, 1)}


def test_system(translate, lang):
    records = []
    for group, professions in (("male_coded", bias.MALE_CODED), ("female_coded", bias.FEMALE_CODED)):
        for profession in professions:
            for template in bias.TEMPLATES:
                text = template.format(p=profession)
                output = translate(text, lang)
                if output is None:
                    continue
                records.append(
                    {
                        "group": group,
                        "profession": profession,
                        "source": text,
                        "translation": output,
                        "gender": bias.detect_gender(output, lang),
                    }
                )

    context = []
    for profession in bias.MALE_CODED + bias.FEMALE_CODED:
        article = "an" if profession[0] in "aeiou" else "a"
        text = bias.CONTEXT_TEMPLATE.format(p=profession).replace(" a ", f" {article} ", 1)
        output = translate(text, lang)
        if output is None:
            continue
        context.append({"source": text, "translation": output, "gender": bias.detect_gender(output, lang)})

    male = rates([r for r in records if r["group"] == "male_coded"])
    female = rates([r for r in records if r["group"] == "female_coded"])
    return {
        "male_coded": male,
        "female_coded": female,
        "stereotype_gap": round(male["masculine_pct"] - female["masculine_pct"], 1),
        "she_respected_pct": round(100 * sum(c["gender"] == "feminine" for c in context) / (len(context) or 1), 1),
        "she_wrong": [c for c in context if c["gender"] == "masculine"][:5],
        "records": records,
    }


def main():
    systems = [("MarianMT", "seq2seq", marian)]
    if llm.available():
        model = llm.models()[llm.available()[0]]
        systems.append((model, "llm", llm_translator(False)))
        systems.append((f"{model} + gender-fair prompt", "llm_fair", llm_translator(True)))

    report = {"templates": bias.TEMPLATES, "languages": {}}
    for lang in LANGUAGES:
        report["languages"][lang] = []
        for name, kind, translate in systems:
            result = test_system(translate, lang)
            report["languages"][lang].append({"system": name, "kind": kind, **result})
            print(
                lang, name,
                "masc% male-coded", result["male_coded"]["masculine_pct"],
                "female-coded", result["female_coded"]["masculine_pct"],
                "gap", result["stereotype_gap"],
                "she kept", result["she_respected_pct"],
            )

    path = ROOT / "results" / "bias.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
