"""HTTP wrapper around engine.py, for hosts with enough memory for PyTorch."""
import base64
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import engine

app = FastAPI(title="Lingo model worker")
WORKER_KEY = os.getenv("WORKER_KEY", "")


def require_key(x_worker_key: str = Header(default="")):
    if WORKER_KEY and x_worker_key != WORKER_KEY:
        raise HTTPException(status_code=401, detail="Invalid worker key")


class Translate(BaseModel):
    text: str = Field(max_length=2000)
    lang: str = Field(pattern="^(hi|mr)$")


class Adequacy(BaseModel):
    source: str = Field(max_length=2000)
    translation: str = Field(max_length=4000)


class Caption(BaseModel):
    image: str


class Imagine(BaseModel):
    prompt: str = Field(max_length=600)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/translate", dependencies=[Depends(require_key)])
def translate(body: Translate):
    return engine.translate(body.text, body.lang)


@app.post("/inspect", dependencies=[Depends(require_key)])
def inspect(body: Translate):
    return engine.inspect(body.text, body.lang)


@app.post("/adequacy", dependencies=[Depends(require_key)])
def adequacy(body: Adequacy):
    return engine.adequacy(body.source, body.translation)


@app.post("/caption", dependencies=[Depends(require_key)])
def caption(body: Caption):
    return engine.caption(base64.b64decode(body.image))


@app.post("/image", dependencies=[Depends(require_key)])
def image(body: Imagine):
    return engine.generate_image(body.prompt)
