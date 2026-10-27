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

# Spracherkennung für den Video-Clipper (Whisper "base", läuft auf der CPU).
# Klappt der Download beim Bauen nicht, lädt die App das Modell beim ersten Clip nach.
RUN python -c "from faster_whisper import download_model; download_model('base', output_dir='/app/models/whisper/base')" \
 || echo "Whisper-Modell kommt beim ersten Clip"

COPY . .

# Version für die Fußzeile der Website (setzt GitHub Actions beim Bauen)
ARG APP_VERSION=dev
ARG APP_BUILT=
ENV APP_VERSION=$APP_VERSION \
    APP_BUILT=$APP_BUILT

VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=1m --timeout=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/dashboard')" || exit 1
CMD ["python", "server.py"]
