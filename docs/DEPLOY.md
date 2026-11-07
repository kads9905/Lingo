# Deployment guide

Everything below is free. You need accounts on GitHub, Groq (or Google AI Studio), Hugging Face, Render and Vercel. Deploy in this order, because each step needs the URL from the one before.

Choose a long random `WORKER_KEY` and keep it for steps 2 and 3:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 1. Push the code to GitHub

Create an empty public repository, then:

```bash
git remote add origin https://github.com/YOUR_NAME/lingo.git
git push -u origin main
```

## 2. Model worker on Hugging Face Spaces

1. Go to huggingface.co/new-space. Name it `lingo-models`, choose the **Docker** SDK and the free **CPU basic** hardware.
2. In **Settings → Variables and secrets**, add a secret named `WORKER_KEY`.
3. Create a write token at huggingface.co/settings/tokens, then upload the worker:

```bash
pip install -U huggingface_hub
```

```bash
hf auth login
```

```bash
hf upload YOUR_NAME/lingo-models backend/ml_worker . --repo-type space
```

The first build takes around 10 to 20 minutes. It is ready when `https://YOUR_NAME-lingo-models.hf.space/health` returns `{"status":"ok"}`.

## 3. Backend on Render

1. In the Render dashboard choose **New → Blueprint** and connect the GitHub repository. It reads `render.yaml`.
2. Fill in these values when asked:

| Key | Value |
| --- | --- |
| `GROQ_API_KEY` | Your Groq key |
| `GEMINI_API_KEY` | Your Gemini key, or leave blank |
| `ML_WORKER_URL` | `https://YOUR_NAME-lingo-models.hf.space` |
| `WORKER_KEY` | The value from the start of this guide |
| `ALLOWED_ORIGINS` | Leave as `http://localhost:5173` for now |

3. Check `https://lingo-api.onrender.com/api/health`. Render may add a suffix to the name.

## 4. Frontend on Vercel

1. In Vercel choose **Add New → Project** and import the repository.
2. Set **Root Directory** to `frontend`. The `frontend/vercel.json` file sets the build.
3. Add the environment variable `VITE_API_URL` with your Render URL and no trailing slash.
4. Deploy.

## 5. Connect them

Set `ALLOWED_ORIGINS` on Render to your Vercel URL, for example `https://lingo.vercel.app`, with no trailing slash. Render redeploys automatically. Without this step the browser blocks every request.

## Before the live demo

Free services sleep: Render after 15 minutes idle, and the Space after a longer period. **Open the app about five minutes before presenting** and run one translation, one photo and one image so everything is awake and loaded.

As a backup, run the app locally with the commands in the README.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Status stays on "Starting" | The Space is asleep or building, or `ML_WORKER_URL` is wrong |
| "Could not reach the server" | `ALLOWED_ORIGINS` or `VITE_API_URL` is wrong |
| LLM shows "No LLM key is configured" | The key is missing on Render |
| "groq returned HTTP 404" | The model was retired. Set `GROQ_MODEL` on Render to a current one |
| "The model worker is unavailable" | `WORKER_KEY` differs between Render and the Space |
