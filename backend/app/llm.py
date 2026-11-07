"""Groq and Gemini chat calls. Keys come from the environment only."""
import os
import re
import time

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(Exception):
    pass


def models():
    return {
        "groq": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "gemini": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    }


def available():
    keys = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}
    return [provider for provider, key in keys.items() if os.getenv(key)]


def _call_groq(messages):
    return httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": models()["groq"], "messages": messages, "temperature": 0.2, "max_tokens": 700},
        timeout=45,
    )


def _call_gemini(messages):
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages[1:]
    ]
    return httpx.post(
        GEMINI_URL.format(model=models()["gemini"]),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        },
        timeout=45,
    )


def _extract(provider, data):
    try:
        if provider == "groq":
            return data["choices"][0]["message"]["content"]
        return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError) as error:
        raise LLMError("The model returned no text.") from error


def _clean(text):
    text = re.sub(r"</?source>", "", text)
    return text.strip().strip('"“”').strip()


def complete(messages, provider=None, retries=0):
    """Returns the reply. `retries` waits out rate limits, which only eval/ needs."""
    enabled = available()
    if not enabled:
        raise LLMError("No LLM key is configured. Set GROQ_API_KEY or GEMINI_API_KEY.")
    provider = provider if provider in enabled else enabled[0]
    call = _call_groq if provider == "groq" else _call_gemini
    start = time.perf_counter()

    for attempt in range(retries + 1):
        try:
            response = call(messages)
        except httpx.HTTPError as error:
            raise LLMError(f"Could not reach {provider}.") from error
        if response.status_code == 429 and attempt < retries:
            time.sleep(float(response.headers.get("retry-after", 20)) + 1)
            continue
        break

    if response.status_code == 429:
        raise LLMError(f"{provider} rate limit reached. Try again in a minute.")
    if response.status_code != 200:
        raise LLMError(f"{provider} returned HTTP {response.status_code}.")
    return {
        "translation": _clean(_extract(provider, response.json())),
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "provider": provider,
        "model": models()[provider],
    }
