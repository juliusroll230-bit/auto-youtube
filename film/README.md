# HyperFrames-Film „60 Sekunden Wissen“

Eine [HyperFrames](https://github.com/heygen-com/hyperframes)-Komposition (HTML → Video), 11 Sekunden, 1080 × 1920.

- **Auf der Homepage** spielt `<hyperframes-player>` sie live ab (siehe `docs/index.html`).
  Player und Laufzeit liegen in `docs/assets/vendor/` (Version 0.8.227), damit die Seite nichts von fremden Servern lädt.
- **Als Video**: `npm run render` erzeugt ein MP4 (Node 22 und FFmpeg nötig). Geeignet als Kanal-Trailer oder Abspann.
- **Bearbeiten**: `npm run dev` öffnet die Vorschau. Texte sind Variablen (`hook`, `claim`, `handle`).
- **Prüfen**: `npm run check` (die Warnungen zu Unter-Kompositionen sind gewollt: eine Datei lädt auf der Website schneller).

Nach Änderungen ein neues Vorschaubild erzeugen:
`ffmpeg -ss 9.6 -i renders/<datei>.mp4 -frames:v 1 -vf scale=540:-1 -q:v 4 poster.jpg`
