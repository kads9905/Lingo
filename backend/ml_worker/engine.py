"""PyTorch models behind the translator: MarianMT, BLIP, MiniLM and SD-Turbo.

Every model loads lazily so the worker starts quickly and only pays for what
is used. Nothing here knows about HTTP; `app.py` and the backend both call it.
"""
import base64
import io
import os
import re
import threading
import time

import torch
from PIL import Image

torch.set_num_threads(int(os.getenv("TORCH_THREADS", min(4, os.cpu_count() or 1))))

# (model, source prefix). opus-mt-en-mr invents content on ordinary sentences, so
# Marathi uses the multi-target Indic model selected with a language token.
MARIAN_MODELS = {
    "hi": ("Helsinki-NLP/opus-mt-en-hi", ""),
    "mr": ("Helsinki-NLP/opus-mt-en-inc", ">>mar<< "),
}
BLIP_MODEL = "Salesforce/blip-image-captioning-base"
BERT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
IMAGE_MODEL = "stabilityai/sd-turbo"

_cache = {}
_lock = threading.Lock()


def _load(key, loader):
    """Imports also happen inside `loader`: concurrent first imports of transformers fail."""
    with _lock:
        if key not in _cache:
            _cache[key] = loader()
        return _cache[key]


def _marian(name):
    def loader():
        from transformers import MarianMTModel, MarianTokenizer

        tokenizer = MarianTokenizer.from_pretrained(name)
        # Eager attention is required for cross-attention weights to be returned.
        model = MarianMTModel.from_pretrained(name, attn_implementation="eager").eval()
        model.generation_config.max_length = None
        return tokenizer, model

    return _load(name, loader)


def _sentences(text):
    """Marian is trained on single sentences, so longer input is split first."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


@torch.inference_mode()
def translate(text, lang, model_name=None, prefix=None):
    """`model_name` and `prefix` override the defaults for the comparison in eval/."""
    default_name, default_prefix = MARIAN_MODELS[lang]
    tokenizer, model = _marian(model_name or default_name)
    prefix = default_prefix if prefix is None else prefix
    start = time.perf_counter()
    parts = []
    for sentence in _sentences(text):
        batch = tokenizer(prefix + sentence, return_tensors="pt", truncation=True, max_length=256)
        output = model.generate(**batch, num_beams=4, max_new_tokens=256)
        parts.append(tokenizer.decode(output[0], skip_special_tokens=True))
    return {
        "translation": " ".join(parts),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }


@torch.inference_mode()
def inspect(text, lang, beams=5):
    """Beam hypotheses with probabilities, plus the cross-attention of the best one."""
    name, prefix = MARIAN_MODELS[lang]
    tokenizer, model = _marian(name)
    sentence = _sentences(text)[0]
    batch = tokenizer(prefix + sentence, return_tensors="pt", truncation=True, max_length=64)
    generated = model.generate(
        **batch,
        num_beams=beams,
        num_return_sequences=beams,
        max_new_tokens=64,
        output_scores=True,
        return_dict_in_generate=True,
    )
    log_probs = generated.sequences_scores
    shares = torch.softmax(log_probs, dim=0)
    alternatives = [
        {
            "text": tokenizer.decode(sequence, skip_special_tokens=True),
            "log_prob": round(float(log_prob), 3),
            "share": round(float(share), 3),
        }
        for sequence, log_prob, share in zip(generated.sequences, log_probs, shares)
    ]

    best = generated.sequences[0]
    best = best[best != model.config.pad_token_id]
    # Teacher-force the winning hypothesis to read one attention map per target token.
    decoder_input = torch.cat([torch.tensor([model.config.decoder_start_token_id]), best]).unsqueeze(0)
    outputs = model(**batch, decoder_input_ids=decoder_input, output_attentions=True)
    attention = outputs.cross_attentions[-1][0].mean(dim=0)[: len(best)]

    return {
        "sentence": sentence,
        "alternatives": alternatives,
        "attention": {
            "source": tokenizer.convert_ids_to_tokens(batch["input_ids"][0]),
            "target": tokenizer.convert_ids_to_tokens(best),
            "weights": [[round(float(w), 4) for w in row] for row in attention],
        },
    }


def _blip():
    def loader():
        from transformers import BlipForConditionalGeneration, BlipProcessor

        return (
            BlipProcessor.from_pretrained(BLIP_MODEL),
            BlipForConditionalGeneration.from_pretrained(BLIP_MODEL).eval(),
        )

    return _load("blip", loader)


@torch.inference_mode()
def caption(image_bytes):
    processor, model = _blip()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((768, 768))
    start = time.perf_counter()
    inputs = processor(images=image, return_tensors="pt")
    output = model.generate(**inputs, num_beams=3, max_new_tokens=30)
    return {
        "caption": processor.decode(output[0], skip_special_tokens=True).strip(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }


def _bert():
    def loader():
        from transformers import AutoModel, AutoTokenizer

        return AutoTokenizer.from_pretrained(BERT_MODEL), AutoModel.from_pretrained(BERT_MODEL).eval()

    return _load("bert", loader)


@torch.inference_mode()
def adequacy(source, translation):
    """Cross-lingual cosine similarity between the English source and its translation."""
    tokenizer, model = _bert()
    batch = tokenizer([source, translation], padding=True, truncation=True, max_length=128, return_tensors="pt")
    hidden = model(**batch).last_hidden_state
    mask = batch["attention_mask"].unsqueeze(-1)
    embeddings = (hidden * mask).sum(1) / mask.sum(1)
    score = torch.nn.functional.cosine_similarity(embeddings[0], embeddings[1], dim=0)
    return {"score": round(float(score), 3)}


def _diffusion():
    def loader():
        from diffusers import AutoPipelineForText2Image

        return AutoPipelineForText2Image.from_pretrained(
            IMAGE_MODEL, torch_dtype=torch.float32, variant="fp16", safety_checker=None
        )

    return _load("diffusion", loader)


@torch.inference_mode()
def generate_image(prompt, size=384):
    pipeline = _diffusion()
    start = time.perf_counter()
    image = pipeline(prompt, num_inference_steps=1, guidance_scale=0.0, width=size, height=size).images[0]
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {
        "image": base64.b64encode(buffer.getvalue()).decode(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }
