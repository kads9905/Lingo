FROM python:3.12-slim
WORKDIR /app
ENV HF_HOME=/app/hf TORCH_THREADS=2
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . ml_worker/
# Bake the core models into the image so a waking Space never has to download them.
RUN python ml_worker/preload.py
EXPOSE 7860
CMD ["uvicorn", "ml_worker.app:app", "--host", "0.0.0.0", "--port", "7860"]
