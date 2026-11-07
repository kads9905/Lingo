"""Runs the PyTorch models in-process, or on a remote worker when ML_WORKER_URL is set."""
import base64
import os

import httpx


class ModelError(Exception):
    pass


def worker_url():
    return os.getenv("ML_WORKER_URL", "").rstrip("/")


def _post(path, payload):
    try:
        response = httpx.post(
            worker_url() + path,
            json=payload,
            headers={"X-Worker-Key": os.getenv("WORKER_KEY", "")},
            timeout=240,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise ModelError("The model worker is unavailable. It may be waking up, so try again shortly.") from error
    return response.json()


def _engine():
    try:
        from ml_worker import engine
    except ImportError as error:
        raise ModelError("The translation models are not connected. Set ML_WORKER_URL on the server.") from error

    return engine


def translate(text, lang):
    if worker_url():
        return _post("/translate", {"text": text, "lang": lang})
    return _engine().translate(text, lang)


def inspect(text, lang):
    if worker_url():
        return _post("/inspect", {"text": text, "lang": lang})
    return _engine().inspect(text, lang)


def adequacy(source, translation):
    if worker_url():
        return _post("/adequacy", {"source": source, "translation": translation})
    return _engine().adequacy(source, translation)


def caption(image_bytes):
    if worker_url():
        return _post("/caption", {"image": base64.b64encode(image_bytes).decode()})
    return _engine().caption(image_bytes)


def generate_image(prompt):
    if worker_url():
        return _post("/image", {"prompt": prompt})
    return _engine().generate_image(prompt)


def worker_ready():
    if not worker_url():
        return True
    try:
        return httpx.get(worker_url() + "/health", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False
