# Auto-YouTube

Erstellt und postet automatisch deutsche YouTube Shorts.

- **Wann:** täglich um 12, 17 und 20 Uhr (deutsche Zeit), über GitHub Actions.
- **Was:** Das nächste Skript aus `content/queue/` wird zum Video (KI-Stimme, Untertitel, Animation) und hochgeladen. Danach landet es in `content/posted/`, und `content/state.json` merkt sich die Uploads.
- **Nachschub:** Neue Skripte werden regelmäßig in `content/queue/` gelegt. Ist die Warteschlange leer, wird nichts gepostet.

## Dateien

| Datei | Zweck |
|---|---|
| `make_short.py` | Baut aus einem Skript ein 1080x1920-Video |
| `car_scene.py` | Hintergrund "Sportwagen bei Nacht" für Skripte mit `"style": "car"` |
| `post_next.py` | Prüft den Zeitplan, rendert und lädt hoch |
| `connect_channel.py` | Verbindet einmalig den YouTube-Kanal |
| `.github/workflows/post.yml` | Der Zeitplan |

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

Für den Auto-Hintergrund statt `colors` und `emoji`: `"style": "car", "car_color": "#d0101c"`.

## Einrichtung

1. **Google Cloud:** Projekt anlegen, "YouTube Data API v3" aktivieren, OAuth-Zustimmungsbildschirm (extern) einrichten und auf "In Produktion" stellen, OAuth-Client vom Typ "Fernseher und Geräte mit begrenzter Eingabe" erstellen.
2. **Kanal verbinden:** `python3 connect_channel.py CLIENT_ID CLIENT_SECRET`, dann den angezeigten Code auf google.com/device eingeben.
3. **GitHub Secrets** im Repo anlegen: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
4. **Öffentliche Uploads:** Google stellt Uploads aus nicht geprüften API-Projekten automatisch auf "privat". Für öffentliche Uploads muss das Projekt das kostenlose YouTube-API-Audit bestehen. Bis dahin die Videos in YouTube Studio selbst auf "öffentlich" stellen.

## Testen

```bash
pip install -r requirements.txt
DRY_RUN=1 python3 post_next.py --force   # rendert das nächste Video, ohne hochzuladen
```

In GitHub: Actions → "Shorts posten" → "Run workflow" mit "force" postet sofort ein Video.

## Hinweise

- Bis zu 6 Uploads pro Tag passen in das kostenlose Standardkontingent der YouTube API. Die Uhrzeiten lassen sich über die Repo-Variable `POST_HOURS` ändern (z. B. `12,15,17,20`).
- Schriften: Inter und Noto Color Emoji (SIL Open Font License, siehe `fonts/`). Stimme: Piper "thorsten" (CC0).
