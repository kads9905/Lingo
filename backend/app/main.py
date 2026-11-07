"""Public API used by the React frontend."""
import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import bias, guardrails, llm, ml_client
from .prompts import LANGUAGES, REGISTERS, TECHNIQUES, build_messages

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
MAX_IMAGE_BYTES = 6_000_000
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

# Local runs read keys from .env; hosted runs get them from the platform's secrets.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if value.strip() and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())

logger = logging.getLogger("lingo")

app = FastAPI(title="Lingo API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

_hits = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Protects the free LLM quota; reads are exempt because the UI polls health."""
    if request.method == "POST":
        client = request.headers.get("x-forwarded-for", request.client.host).split(",")[0]
        now = time.monotonic()
        hits = _hits[client]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= RATE_LIMIT:
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
        hits.append(now)
    return await call_next(request)


@app.exception_handler(Exception)
async def on_unexpected(request, error):
    logger.exception("Unhandled error on %s", request.url.path, exc_info=error)
    return JSONResponse({"detail": "Something went wrong. Please try again."}, status_code=500)


@app.exception_handler(guardrails.Blocked)
async def on_blocked(_, error):
    return JSONResponse({"detail": str(error)}, status_code=422)


@app.exception_handler(ml_client.ModelError)
async def on_model_error(_, error):
    return JSONResponse({"detail": str(error)}, status_code=503)


class TranslateBody(BaseModel):
    text: str
    lang: str = Field(pattern="^(hi|mr)$")
    tone: str = "neutral"
    technique: str = "zero_shot"
    provider: str | None = None


class TextBody(BaseModel):
    text: str
    lang: str = Field(pattern="^(hi|mr)$")


class ImagineBody(BaseModel):
    prompt: str


class ProbeBody(BaseModel):
    profession: str = Field(min_length=2, max_length=40)
    lang: str = Field(pattern="^(hi|mr)$")
    provider: str | None = None


def _check_options(tone, technique):
    if tone not in REGISTERS or technique not in TECHNIQUES:
        raise HTTPException(status_code=422, detail="Unknown register or technique.")


def _score(source, candidate):
    candidate["adequacy"] = ml_client.adequacy(source, candidate["translation"])["score"]
    candidate["warnings"] = guardrails.check_output(candidate["translation"], candidate["adequacy"])[1]
    return candidate


def _seq2seq(text, lang):
    return _score(text, ml_client.translate(text, lang))


def _llm(text, lang, tone, technique, provider):
    try:
        reply = llm.complete(build_messages(text, lang, tone, technique), provider)
    except llm.LLMError as error:
        return {"error": str(error)}
    valid, warnings = guardrails.check_output(reply["translation"])
    if not valid:
        return {"error": warnings[0]}
    return _score(text, reply)


async def _translate_both(text, lang, tone, technique, provider):
    seq2seq, reply = await asyncio.gather(
        asyncio.to_thread(_seq2seq, text, lang),
        asyncio.to_thread(_llm, text, lang, tone, technique, provider),
    )
    return {"seq2seq": seq2seq, "llm": reply}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "models_ready": ml_client.worker_ready(),
        "providers": [{"id": p, "model": llm.models()[p]} for p in llm.available()],
    }


@app.get("/api/options")
def options():
    return {
        "languages": LANGUAGES,
        "registers": {key: {"label": r["label"], "hint": r["hint"]} for key, r in REGISTERS.items()},
        "techniques": TECHNIQUES,
        "professions": {"male_coded": bias.MALE_CODED, "female_coded": bias.FEMALE_CODED},
    }


@app.post("/api/translate")
async def translate(body: TranslateBody):
    _check_options(body.tone, body.technique)
    warnings = guardrails.check_input(body.text)
    result = await _translate_both(body.text.strip(), body.lang, body.tone, body.technique, body.provider)
    return {"warnings": warnings, **result}


@app.post("/api/inspect")
async def inspect(body: TextBody):
    guardrails.check_input(body.text)
    return await asyncio.to_thread(ml_client.inspect, body.text.strip(), body.lang)


@app.post("/api/caption")
async def caption(
    image: UploadFile = File(),
    lang: str = Form(pattern="^(hi|mr)$"),
    tone: str = Form("neutral"),
    technique: str = Form("zero_shot"),
    provider: str | None = Form(None),
):
    _check_options(tone, technique)
    if not (image.content_type or "").startswith("image/"):
        raise guardrails.Blocked("Please upload an image file.")
    data = await image.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise guardrails.Blocked("Please upload an image under 6 MB.")
    described = await asyncio.to_thread(ml_client.caption, data)
    result = await _translate_both(described["caption"], lang, tone, technique, provider)
    return {"caption": described["caption"], "caption_ms": described["latency_ms"], **result}


@app.post("/api/tts")
async def tts(body: TextBody):
    from gtts import gTTS
    from gtts.tts import gTTSError

    if not 0 < len(body.text) <= guardrails.MAX_CHARS * 2:
        raise guardrails.Blocked("There is no translation to speak.")

    def speak():
        buffer = BytesIO()
        gTTS(body.text, lang=body.lang, tld="co.in").write_to_fp(buffer)
        return buffer.getvalue()

    try:
        audio = await asyncio.to_thread(speak)
    except AssertionError as error:
        raise guardrails.Blocked("There is no text to speak.") from error
    except gTTSError as error:
        raise HTTPException(status_code=502, detail="Speech service is unavailable.") from error
    return Response(audio, media_type="audio/mpeg")


@app.post("/api/imagine")
async def imagine(body: ImagineBody):
    guardrails.check_input(body.prompt)
    return await asyncio.to_thread(ml_client.generate_image, body.prompt.strip())


@app.post("/api/bias/probe")
async def bias_probe(body: ProbeBody):
    text = bias.TEMPLATES[0].format(p=body.profession.strip())
    guardrails.check_input(text)

    def run_llm(gender_fair):
        try:
            messages = build_messages(text, body.lang, gender_fair=gender_fair)
            reply = llm.complete(messages, body.provider)["translation"]
        except llm.LLMError as error:
            return {"error": str(error)}
        return {"translation": reply, "gender": bias.detect_gender(reply, body.lang)}

    seq2seq, plain, fair = await asyncio.gather(
        asyncio.to_thread(ml_client.translate, text, body.lang),
        asyncio.to_thread(run_llm, False),
        asyncio.to_thread(run_llm, True),
    )
    return {
        "sentence": text,
        "seq2seq": {
            "translation": seq2seq["translation"],
            "gender": bias.detect_gender(seq2seq["translation"], body.lang),
        },
        "llm": plain,
        "llm_fair": fair,
    }


@app.get("/api/results")
def results():
    merged = {}
    for name in ("bleu", "bias", "adequacy"):
        path = RESULTS_DIR / f"{name}.json"
        merged[name] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return merged
