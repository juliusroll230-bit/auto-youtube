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
# curl mit Wiederholungen: GitHub liefert beim Bauen manchmal kurz eine Fehlerseite statt der Datei.
RUN mkdir -p models \
 && curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors -o /tmp/voice.tar.bz2 \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-de_DE-thorsten-high.tar.bz2 \
 && tar xjf /tmp/voice.tar.bz2 -C models \
 && rm /tmp/voice.tar.bz2

# Spracherkennung für den Video-Clipper (Whisper "base", läuft auf der CPU).
# Klappt der Download beim Bauen nicht, lädt die App das Modell beim ersten Clip nach.
RUN python -c "from faster_whisper import download_model; download_model('base', output_dir='/app/models/whisper/base')" \
 || echo "Whisper-Modell kommt beim ersten Clip"

# Browser für die Cartoon-Shorts (zeichnet die Strichmännchen-Szenen, siehe cartoon.py)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps --only-shell chromium \
 && rm -rf /var/lib/apt/lists/*

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
