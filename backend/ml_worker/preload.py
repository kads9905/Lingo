"""Downloads the core models at image build time. SD-Turbo stays lazy because of its size."""
from transformers import AutoModel, AutoTokenizer, BlipForConditionalGeneration, BlipProcessor
from transformers import MarianMTModel, MarianTokenizer

for name in ("Helsinki-NLP/opus-mt-en-hi", "Helsinki-NLP/opus-mt-en-inc"):
    MarianTokenizer.from_pretrained(name)
    MarianMTModel.from_pretrained(name)

BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
AutoTokenizer.from_pretrained(name)
AutoModel.from_pretrained(name)
