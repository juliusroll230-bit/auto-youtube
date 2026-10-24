# Shorts-Zentrale

Erstellt und postet automatisch deutsche YouTube Shorts und zeigt alles auf einer Website: Sendeplan, gepostete Videos, Bestenliste und die Kanal-Verbindung. Läuft als ein Docker-Container, zum Beispiel auf einem ZimaOS-Server.

## Installation auf ZimaOS

1. ZimaOS öffnen → **App Store** → oben rechts **+** → **Benutzerdefinierte App installieren** → **Importieren**.
2. Den Inhalt von [`docker-compose.yml`](docker-compose.yml) einfügen und installieren.
3. Die App öffnen: `http://<IP-deines-Servers>:8090`
4. Im Reiter **Kanal** Client-ID und Clientschlüssel eintragen (Anleitung steht dort) und auf **Mit YouTube verbinden** tippen.

Die Daten liegen auf dem Server unter `/DATA/AppData/shorts-zentrale`.

## So funktioniert es

- **Hintergründe:** Jedes Thema hat einen eigenen bewegten Hintergrund, der sich bei jedem Satz ändert (Psychologie: Nervenzellen, Geschichte: Bauwerke im Abendlicht, Geld: Börsenkurs und Münzen, Geografie: drehende Erde mit Markierung, Business: Autofahrt mit wechselnder Tageszeit). Siehe `themes.py` und `car_scene.py`.
- **Kanal-Design:** Banner, Kanalbeschreibung und Stichwörter setzt die App automatisch (`branding.py`). Das Profilbild erlaubt YouTube nur von Hand.
- **Zeitplan:** Zu jeder Sendezeit (Standard 8, 11, 13, 16, 18 und 20 Uhr, also 6 am Tag; mehr erlaubt die YouTube-Schnittstelle pro Tag nicht) wird das nächste Skript aus der Warteschlange zum Video (KI-Stimme, Untertitel, Animation) und hochgeladen. Die Zeiten lassen sich im Reiter **Kanal** ändern.
- **Nachschub:** Alle 2 Stunden holt die App neue Skripte aus dem Ordner `seed/` dieses Repos (`SCRIPTS_REPO`).
- **Statistiken:** Aufrufe, Likes und Kommentare kommen alle 3 Stunden von YouTube.
- **Lernmodus:** Am Anfang wechseln sich die Themen ab. Sobald jedes Thema 2 Videos mit Aufrufen hat, kommen 3 von 4 Videos aus dem Thema mit den meisten Aufrufen (hochgerechnet auf die ersten 3 Tage), jedes 4. testet ein anderes. Details in `learn.py`, die Übersicht steht im Reiter **Bestenliste**.
- **Updates:** Jede Code-Änderung baut über GitHub Actions ein neues Image `ghcr.io/<besitzer>/auto-youtube:latest`. Automatisch übernehmen: zusätzlich [`updater/docker-compose.yml`](updater/docker-compose.yml) in ZimaOS importieren. Der Updater prüft beim Start und jede Nacht um 4 Uhr und tauscht nur den Container `shorts-zentrale` aus (außerhalb der Sendezeiten).

## Dateien

| Datei | Zweck |
|---|---|
| `server.py` | Website, Zeitplan, Uploads |
| `store.py` | Speichert Einstellungen, Warteschlange und Statistiken in `/data` |
| `yt.py` | YouTube: Anmeldung per Geräte-Code, Upload, Statistiken |
| `make_short.py` | Baut aus einem Skript ein 1080x1920-Video |
| `car_scene.py` | Hintergrund "Sportwagen bei Nacht" für Skripte mit `"style": "car"` |
| `web/index.html` | Die Website |
| `seed/` | Skripte für die Warteschlange |

## Skript-Format

```json
{
  "slug": "eindeutiger-name",
  "niche": "Psychologie",
  "colors": ["#2b1055", "#7597de"],
  "accent": "#ffd166",
  "title": "Titel mit Emoji 🧠",
  "description": "Beschreibung mit #hashtags",
  "tags": ["psychologie", "shorts"],
  "segments": [{"emoji": "🧠", "text": "Ein Satz, der vorgelesen wird."}]
}
```

Für den Auto-Hintergrund statt `colors` und `emoji`: `"style": "car", "car_color": "#d0101c"`. Dateinamen sind fortlaufend nummeriert (`0016-slug.json`), die kleinste Nummer wird zuerst gepostet.

## Einstellungen (Umgebungsvariablen)

| Variable | Bedeutung |
|---|---|
| `PASSWORD` | schützt die Website (Benutzer `admin`) |
| `SCRIPTS_REPO` | Repo, aus dem neue Skripte kommen |
| `GITHUB_TOKEN` | nur nötig, wenn dieses Repo privat ist |

## Hinweise

- Google stellt Uploads aus neuen, nicht geprüften API-Projekten automatisch auf **privat**. Für automatisch öffentliche Videos muss das Projekt das kostenlose YouTube-API-Audit bestehen.
- Solange die Google-App im Status „Test“ ist, läuft die Verbindung alle 7 Tage ab. Die Website zeigt das an, dann im Reiter **Kanal** einfach neu verbinden. Zum Veröffentlichen der Google-App braucht es eine Startseite mit Datenschutzerklärung.
- Das kostenlose API-Kontingent reicht für bis zu 6 Uploads pro Tag.
- Die Website nur im Heimnetz nutzen oder mit `PASSWORD` schützen.
- Lokal starten ohne Docker: `pip install -r requirements.txt`, Stimme nach `models/` laden (siehe `Dockerfile`), dann `python3 server.py`.
- Schriften: Inter und Noto Color Emoji (SIL Open Font License, siehe `fonts/`). Stimme: Piper "thorsten" (CC0).
