# Model card: Lingo

## Summary

Lingo translates English into Hindi and Marathi with two systems side by side: a pretrained MarianMT encoder–decoder and a hosted LLM. No model was trained or fine-tuned for this project. The LLM is adapted through prompts only.

## Models

| Model | Purpose | Licence |
| --- | --- | --- |
| Helsinki-NLP/opus-mt-en-hi | Hindi seq2seq | Apache 2.0 |
| Helsinki-NLP/opus-mt-en-inc | Marathi seq2seq, with the `>>mar<<` token | Apache 2.0 |
| Groq `openai/gpt-oss-120b` or Gemini `gemini-3.5-flash-lite` | LLM translation | Apache 2.0 weights for gpt-oss, plus each provider's terms |
| Salesforce/blip-image-captioning-base | Image captions | BSD 3-Clause |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | BERT-family meaning check | Apache 2.0 |
| stabilityai/sd-turbo | Image generation | Stability AI community licence, with limits on commercial use |
| gTTS | Speech | MIT library that calls an unofficial Google Translate endpoint |

`Helsinki-NLP/opus-mt-en-mr` was tested and rejected because it invents content. See `backend/results/bleu.json`.

## Intended use

Everyday text, learning, and comparing translation approaches.

## Not intended for

Medical, legal, immigration, safety-critical or official documents without a human translator.

## Evaluation

- **Quality:** corpus BLEU and chrF on 20 hand-written reference sentences in each language.
- **Bias:** 60 ungendered profession sentences and 20 sentences with an explicit "she", per language and system.
- **Guardrail:** the meaning check on correct and deliberately mismatched pairs.

Measured values are in `backend/results/`, on the app's Results tab, and in `docs/report.pdf`.

The reference translations were drafted with AI assistance, so a fluent speaker should review them before the scores are treated as final. With only 20 sentences and one reference each, small BLEU differences are not meaningful.

## Known limits

- **Gender:** Hindi and Marathi verbs often mark gender, which English does not. Models assign one anyway, and MarianMT can ignore an explicit "she".
- **Idioms:** MarianMT translates many idioms word for word.
- **Hallucination:** MarianMT can produce fluent text unrelated to the source, or fragments, especially in Marathi.
- **Rare words:** infrequent professions can be mistranslated or transliterated wrongly.
- **Meaning check:** it catches unrelated text but flagged only 1 of MarianMT's 10 lowest-BLEU outputs, so it misses translations that are wrong yet on topic, such as literal idioms.
- **Captions:** BLIP gives short, generic English captions, and any error carries into the translation.

## Safety

- Input length limit, and a filter for clearly harmful requests.
- Text is delimited and treated as data, so instructions inside it are translated rather than obeyed.
- LLM output that is not Devanagari is withheld.
- A low meaning-match score shows a warning.
- A notice appears when the English leaves a person's gender unstated.
- Requests are rate limited per client.

The keyword filter is simple and is not a complete content moderation system.

## Data and privacy

Text and images are processed in memory and not stored by this app. Text sent to the LLM goes to Groq or Google, and text sent for speech goes to Google, under their terms. Do not enter personal or confidential information.

## IP note

Rights in user input stay with the user. Rights in machine output vary by jurisdiction. Generated images must follow the SD-Turbo licence, which matters if this project is ever used commercially.
