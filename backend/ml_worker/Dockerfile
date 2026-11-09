FROM python:3.12-slim
# Hugging Face Spaces run containers as user 1000, so the model cache must belong to that user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/hf TORCH_THREADS=2
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY --chown=user . ml_worker/
# Bake the core models into the image so a waking Space never has to download them.
RUN python ml_worker/preload.py
EXPOSE 7860
CMD ["uvicorn", "ml_worker.app:app", "--host", "0.0.0.0", "--port", "7860"]
