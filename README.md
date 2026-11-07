# Lingo

English to Hindi and Marathi translation that compares an encoder–decoder model with an LLM, for typed text and for image captions. Project P19.

**Live app:** add your Vercel URL here after deploying.

## What it does

| Task | Feature |
| --- | --- |
| U1 | Tone prompts for the LLM: neutral, formal, casual, for children. Zero-shot or few-shot. |
| U2 | MarianMT and a Groq or Gemini LLM translate side by side, with latency and a meaning-match score. |
| U3 | Upload a photo, BLIP captions it, and both models translate the caption. |
| U4 | Listen to any translation with gTTS. |
| U5 | The Bias lab tests whether a profession gets a gender the English never stated. |

It also shows MarianMT's cross-attention and beam probabilities, and generates images with SD-Turbo.

## Project structure

```
Encode-decode/
├── frontend/              Deploy to Vercel (configured by vercel.json)
│   └── src/
├── backend/               Deploy to Render (rootDir: backend, set in render.yaml)
│   ├── app/               FastAPI app, prompts, guardrails, LLM calls
│   ├── ml_worker/         PyTorch models. Deploy this folder to a Hugging Face Space
│   ├── eval/              BLEU, bias and guardrail evaluations
│   ├── data/              The 20 reference sentences
│   ├── results/           Measured results, shown on the Results page
│   ├── tests/
│   └── requirements.txt   Render installs only this light list
├── docs/                  Report, deployment guide, demo script
├── render.yaml            Render blueprint
├── vercel.json            Vercel build settings
└── MODEL_CARD.md
```

## Architecture

```
Vercel (frontend)  ──▶  Render (backend)  ──▶  Groq / Gemini
                             │
                             ├──▶  gTTS
                             └──▶  Hugging Face Space (ml_worker)
```

The backend holds the API keys and runs the guardrails. PyTorch with one MarianMT model measured 808 MB of RAM, which does not fit Render's free 512 MB instance, so the models run on a free Hugging Face Space. If `ML_WORKER_URL` is empty, the backend runs them in-process instead, which suits local use or a paid Render plan with at least 4 GB.

## Deploy

Follow [docs/DEPLOY.md](docs/DEPLOY.md). API keys belong in each platform's secret settings, never in this repository.

## Run locally

Requires Python 3.12+ and Node 20+.

Set up the backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
cp .env.example .env
```

Put `GROQ_API_KEY` or `GEMINI_API_KEY` in `backend/.env`, then start it:

```bash
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Reproduce the results

Run these from `backend/`:

```bash
.venv/Scripts/python -m eval.run_bleu
```

```bash
.venv/Scripts/python -m eval.run_bias
```

```bash
.venv/Scripts/python -m eval.run_adequacy
```

```bash
.venv/Scripts/python -m eval.build_report
```

Results go to `backend/results/`, where the Results page reads them. The last command rebuilds `docs/report.pdf`.

## Tests

```bash
.venv/Scripts/python -m pytest tests
```

See [MODEL_CARD.md](MODEL_CARD.md) for limits and licences.
