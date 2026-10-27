# Shorts-Zentrale

Erstellt und postet automatisch deutsche YouTube Shorts und zeigt alles auf einer Website: Kennzahlen mit Diagrammen, wann Zuschauer abschalten, gepostete Videos, Sendeplan und die Kanal-Verbindung. Läuft als ein Docker-Container, zum Beispiel auf einem ZimaOS-Server.

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
- **Statistiken:** Aufrufe, Likes und Kommentare kommen alle 20 Minuten von YouTube. Daraus entsteht auch der Verlauf (`history.json`) für das Wachstums-Diagramm.
- **Zuschauer-Daten:** Optional holt die App alle 3 Stunden aus YouTube Analytics, wie viel von jedem Video angesehen wird und an welcher Stelle Zuschauer abschalten. Die Website zeigt das im Reiter **Zuschauer** als Kurve mit den Satzanfängen und als Verlust je Satz. Einrichten: siehe unten.
- **Ton und Bild:** Die Stimme läuft durch einen Kompressor und wird auf die YouTube-Lautheit (-14 LUFS) gebracht, Ton in 48 kHz. Das Video wird in hoher Qualität kodiert (H.264 High, CRF 18).
- **Kopfzeile:** Bei manchen Videos steht der Titel vom ersten Bild an oben als Kopfzeile. Ob das mehr Aufrufe bringt, testet der Lernmodus selbst.
- **Lernmodus:** Am Anfang wechseln sich die Themen ab. Sobald jedes Thema 2 Videos mit Aufrufen hat, kommen 3 von 4 Videos aus dem Thema mit den meisten Aufrufen (hochgerechnet auf die ersten 3 Tage), jedes 4. testet ein anderes. Mit Zuschauer-Daten zählen Themen mehr, bei denen die Leute länger dranbleiben. Genauso wählt die App Untertitel-Stil, Übergang und Kopfzeile. Details in `learn.py`, die Übersicht steht im Reiter **Zuschauer**.
- **Zentrale (Startseite):** Die Website zeigt jede Aufgabe der App als eigenen KI-Agenten im "Brain Room": Das Gehirn (Lernmodus), Writers' Room (Skripte holen), Sprecher, Video-Studio, Publisher (Upload), Analyst (Statistiken), Research (Zuschauer-Daten) und Designer (Kanal-Design). Antippen öffnet ein Bedienfeld mit Status, Kennzahlen, Schaltern und Reglern (z. B. Sprechtempo, wie oft der Analyst abfragt, Kopfzeile immer/nie/selbst lernen) und dem Knopf zum sofortigen Starten. Sprecher und Studio zeigen dort eine Hörprobe bzw. ein Vorschaubild. Die Einstellungen liegen in `config.json` unter `agents`, siehe `agents.py`.
- **Freigabe-Station:** Normalerweise geht jedes Video automatisch online. Mit "Ablehnen" nimmt man ein Video aus dem Plan (es landet in `rejected/` und lässt sich wiederherstellen). Mit eingeschalteter Freigabe-Pflicht postet der Publisher nur Videos, die vorher freigegeben wurden.
- **Live-Feed:** Zeigt, welcher Agent gerade arbeitet, und die letzten Ereignisse.
- **Updates:** Jede Code-Änderung baut über GitHub Actions ein neues Image `ghcr.io/<besitzer>/auto-youtube:latest`. Automatisch übernehmen: zusätzlich [`updater/docker-compose.yml`](updater/docker-compose.yml) in ZimaOS importieren. Der Updater prüft beim Start und jede Nacht um 4 Uhr und tauscht nur den Container `shorts-zentrale` aus (außerhalb der Sendezeiten).

## Dateien

| Datei | Zweck |
|---|---|
| `server.py` | Website, Zeitplan, Uploads |
| `store.py` | Speichert Einstellungen, Warteschlange und Statistiken in `/data` |
| `agents.py` | Die Agenten der Zentrale: Einstellungen, Status und Kennzahlen |
| `learn.py` | Lernmodus: wählt Thema und Look nach Erfolg |
| `yt.py` | YouTube: Anmeldung per Geräte-Code, Upload, Statistiken, Zuschauer-Daten (Analytics) |
| `make_short.py` | Baut aus einem Skript ein 1080x1920-Video |
| `car_scene.py` | Hintergrund "Sportwagen bei Nacht" für Skripte mit `"style": "car"` |
| `web/index.html` | Die Website |
| `docs/` | Startseite, Datenschutz und `oauth.html` (Weiterleitung für die Zuschauer-Daten) auf GitHub Pages |
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

Im Text markieren Sternchen ein Schlüsselwort (`*Toyota*`), es wird im Untertitel farbig und größer gezeigt; vorgelesen wird es ohne Sternchen. Steht nach einer Zahl eine großgeschriebene Einheit („sechshundert Kilometer“), zeigt das Video einen Zähler, der bis zu dieser Zahl hochzählt.

Ein Segment kann eine Grafik bekommen: `"visual": {"type": "zeitstrahl" | "vergleich" | "liste" | "anteil" | "wort", ...}` (Beispiele oben in `visuals.py`). Jedes Video bekommt außerdem einen eigenen Untertitel-Stil und eigene Übergänge.

Für den Auto-Hintergrund statt `colors` und `emoji`: `"style": "car", "car_color": "#d0101c"`. Dateinamen sind fortlaufend nummeriert (`0016-slug.json`), die kleinste Nummer wird zuerst gepostet.

## Einstellungen (Umgebungsvariablen)

| Variable | Bedeutung |
|---|---|
| `PASSWORD` | schützt die Website (Benutzer `admin`) |
| `SCRIPTS_REPO` | Repo, aus dem neue Skripte kommen |
| `GITHUB_TOKEN` | nur nötig, wenn dieses Repo privat ist |
| `OAUTH_PAGE` | Weiterleitungsseite für die Zuschauer-Daten (Standard: `https://<besitzer>.github.io/<repo>/oauth.html`) |

## Zuschauer-Daten einrichten

Die Anmeldung per Geräte-Code erlaubt nur Upload-Rechte, nicht YouTube Analytics. Darum gibt es einen zweiten Google-Zugang vom Typ **Webanwendung**:

1. In Google Cloud die **YouTube Analytics API** aktivieren.
2. Unter Google Auth Platform → Clients einen Client vom Typ **Webanwendung** anlegen, Weiterleitungs-URI: `https://<besitzer>.github.io/<repo>/oauth.html`.
3. Client-ID und Clientschlüssel auf der Website im Reiter **Zuschauer** eintragen und **Verbinden** klicken.

Google schickt nach der Anmeldung zu `oauth.html`; die Seite leitet den Code an die Shorts-Zentrale im Heimnetz weiter (die Adresse des Servers steht im `state`, der Server prüft ihn mit einer Einmal-Nummer). Darum klappt das Verbinden nur im selben Netz wie der Server. YouTube liefert die Werte mit 1 bis 3 Tagen Verzögerung.

## Hinweise

- Google stellt Uploads aus neuen, nicht geprüften API-Projekten automatisch auf **privat**. Für automatisch öffentliche Videos muss das Projekt das kostenlose YouTube-API-Audit bestehen.
- Solange die Google-App im Status „Test“ ist, läuft die Verbindung alle 7 Tage ab. Die Website zeigt das an, dann im Reiter **Kanal** einfach neu verbinden. Zum Veröffentlichen der Google-App braucht es eine Startseite mit Datenschutzerklärung.
- Das kostenlose API-Kontingent reicht für bis zu 6 Uploads pro Tag.
- Die Website nur im Heimnetz nutzen oder mit `PASSWORD` schützen.
- Lokal starten ohne Docker: `pip install -r requirements.txt`, Stimme nach `models/` laden (siehe `Dockerfile`), dann `python3 server.py`.
- Schriften: Inter und Noto Color Emoji (SIL Open Font License, siehe `fonts/`). Stimme: Piper "thorsten" (CC0).
