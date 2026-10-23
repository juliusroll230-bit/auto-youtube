FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    PORT=8080 \
    TTS_MODEL_DIR=/app/models/vits-piper-de_DE-thorsten-high

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg curl bzip2 ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Deutsche Stimme "thorsten" (Piper, CC0)
RUN mkdir -p models \
 && curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-de_DE-thorsten-high.tar.bz2 \
    | tar xj -C models

COPY . .

VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=1m --timeout=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/dashboard')" || exit 1
CMD ["python", "server.py"]
