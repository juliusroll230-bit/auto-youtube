# Cartoon-Shorts (Strichmännchen-Baukasten)

Ein Skript in `seed/` wird zum Cartoon, wenn es `"stil": "cartoon"` hat. Stimme, Musik und Upload laufen wie bei
allen Shorts. Das Bild baut `cartoon.py` aus fertigen Szenen in `cartoon/web/scenes.js` und rendert es mit Chromium.
Figuren, Gesichter und Hilfsfunktionen stammen aus
[claude-animation-skills](https://github.com/artemnovitckii/claude-animation-skills) (MIT, siehe `LICENSE-stick-figure.txt`).

Prüfen: `python cartoon.py seed/0109-geschichte-tanzwut-1518.json --check` (gibt `ok` oder die Fehler aus).
Test-Video: `python cartoon.py skript.json ausgabe/`.

## Aufbau

```json
{
  "slug": "geschichte-tanzwut-1518", "stil": "cartoon", "niche": "Geschichte",
  "colors": ["#2a1f3d", "#7a4bc4"], "accent": "#ffe14d",
  "title": "Die Stadt, die nicht aufhören konnte zu tanzen 💃",
  "description": "…\n\n#geschichte #wissen #shorts", "tags": ["geschichte", "wissen", "shorts"],
  "figur": {"farbe": "lila", "hut": "keiner"},
  "segments": [
    {"text": "Ein Satz, höchstens 14 Wörter.", "szene": {"typ": "figur", "ort": "dorf", "gefuehl": "staunen", "aktion": "jubelt"}}
  ]
}
```

- 6 bis 12 Segmente, **ein Satz pro Segment** (jedes Segment ist eine Einstellung mit Wisch-Übergang).
- `figur` oben ist die Hauptfigur des ganzen Videos; eine Szene kann mit eigenem `figur` eine andere zeigen.
- Zahlen im Text als Wörter ("fünfzehnhundertachtzehn"), die Untertitel zeigen Ziffern.

## Szenen (`szene`)

| typ | zeigt | Felder |
|---|---|---|
| `figur` | Hauptfigur an einem Ort | `ort`, `gefuehl`, `aktion`, optional `objekt` (Emoji schwebt daneben), `text` (Schild oben) |
| `zwei` | zwei Figuren, die zweite reagiert | `ort`, `gefuehl`, `aktion`, `zweite: {farbe, hut, gefuehl, aktion}`, optional `text` |
| `gruppe` | Menschenmenge (3 bis 7) | `ort`, `anzahl`, `gefuehl`, `aktion`, optional `text` |
| `objekt` | großes Emoji mit Strahlen | `objekt`, optional `ort` (abgedunkelt), `text` |
| `zahl` | großer Zähler | `zahl` (Zahl), `einheit`, optional `objekt`, `farbcode` (#rrggbb) |
| `jahr` | Notizzettel mit Jahreszahl | `jahr`, optional `text`, `objekt`, `stempel` (z. B. "wahr", "geheim") |
| `liste` | Checkliste auf Papier | `text` (Überschrift), `punkte` (2 bis 4) |
| `vergleich` | rot gegen blau | `links: {objekt, text}`, `rechts: {objekt, text}` |
| `horror` | dunkler Raum, Taschenlampe, leuchtende Augen | `ort` (keller, nacht, haus, kinderzimmer …), `gefuehl`, `aktion`, optional `objekt`, `text`, `augen` (#farbe) |

- `ort`: strand, meer, stadt, wald, feld, nacht, haus, kinderzimmer, keller, schule (mit `tafel`: Text an der Tafel), buero, labor, weltall, wueste, burg, dorf, farbe
- `gefuehl`: freude, angst, staunen, wut, traurig, denken, cool, neutral, k_o
- `aktion`: steht, zeigt, winkt, jubelt, rennt, zittert, denkt, faellt, schockiert, haende
- `farbe`: rot, blau, gelb, gruen, lila, navy · `hut`: keiner, bandana, matrose, kapitaen, krone, zylinder, helm, muetze, hexe, ritter
- `text` und `tafel` höchstens 22 Zeichen.
