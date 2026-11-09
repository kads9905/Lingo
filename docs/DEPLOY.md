# Deployment guide

Everything below is free. You need accounts on GitHub, Groq (or Google AI Studio), Render and Vercel, and the free cloudflared tool on your laptop. Deploy in this order, because each step needs the URL from the one before.

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

## 2. Model worker on your laptop

Hugging Face now charges for Docker Spaces, so the PyTorch models run on your own computer and are reached through a free Cloudflare tunnel.

Install the tunnel tool once:

```bash
winget install --id Cloudflare.cloudflared
```

Add a `WORKER_KEY` line to `backend/.env` with the value you generated above. Then, from the `backend` folder, start the worker:

```bash
..\.venv\Scripts\python start_worker.py
```

It loads the models, opens the tunnel and prints an `ML_WORKER_URL` such as `https://example-words.trycloudflare.com`. Keep the window open.

**The tunnel address changes every time the script starts**, so update `ML_WORKER_URL` on Render each time, then redeploy.

If you have a Hugging Face PRO subscription, you can instead upload `backend/ml_worker` as a Docker Space and use its permanent address.

## 3. Backend on Render

1. In the Render dashboard choose **New → Blueprint** and connect the GitHub repository. It reads `render.yaml`.
2. Fill in these values when asked:

| Key | Value |
| --- | --- |
| `GROQ_API_KEY` | Your Groq key |
| `GEMINI_API_KEY` | Your Gemini key, or leave blank |
| `ML_WORKER_URL` | The address printed by `start_worker.py` |
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

1. Keep the laptop awake and online, and run `start_worker.py`.
2. Copy its new `ML_WORKER_URL` into Render and choose **Save, rebuild, and deploy**.
3. Render's free service sleeps after 15 minutes idle. **Open the app about five minutes before presenting** and run one translation, one photo and one image so everything is awake.

As a backup, run the app locally with the commands in the README.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Status stays on "Starting" | Render is waking up, or the worker script is not running |
| "Could not reach the server" | `ALLOWED_ORIGINS` or `VITE_API_URL` is wrong |
| LLM shows "No LLM key is configured" | The key is missing on Render |
| "groq returned HTTP 404" | The model was retired. Set `GROQ_MODEL` on Render to a current one |
| "The model worker is unavailable" | The worker script stopped, the tunnel address changed, or `WORKER_KEY` differs between Render and `backend/.env` |
| "The translation models are not connected" | `ML_WORKER_URL` is missing on Render, or Render was saved without redeploying |
