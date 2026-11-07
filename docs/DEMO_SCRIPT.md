# Demo script (about 2 minutes 30 seconds)

Wake the app five minutes before recording. Show the public URL in the address bar.

**0:00 Intro (15 s).** "This is Lingo. It translates English into Hindi and Marathi, and compares a classic encoder–decoder model with a modern LLM."

**0:15 Translate (40 s).** Type "Heavy rain has caused floods in several districts." Translate into Hindi. Point out both results, latency and the meaning-match score. Switch the tone to Formal and translate again to show that the LLM changes register and MarianMT cannot. Click Listen.

**0:55 Internals (20 s).** Open Model internals. Explain that the attention grid shows which English word the decoder used for each output word, and that beam search shows the sentences it nearly chose.

**1:15 Photo (25 s).** Upload a photo. BLIP captions it, both models translate it, and it can be spoken.

**1:40 Imagine (10 s).** Generate one image with SD-Turbo.

**1:50 Bias lab (20 s).** Try "nurse", then "engineer". Show the gender assigned by each model, and what the gender-fair prompt changes.

**2:10 Results and failure (20 s).** Open Results. State the BLEU comparison. Show one failure: "It is raining cats and dogs outside" translated word for word by MarianMT. Mention the "she" failure from the bias table.

**2:30 Close (5 s).** "It runs on Vercel, Render and a Hugging Face Space, with keys held in platform secrets."
