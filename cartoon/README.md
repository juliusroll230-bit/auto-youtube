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

- 7 bis 9 Segmente (erlaubt 6 bis 12), **ein Satz pro Segment** (jedes Segment ist eine Einstellung mit Wisch-Übergang), zusammen 60 bis 85 Wörter (höchstens 95). Kurz und schnell: der erste Satz wirft die Zuschauer mitten ins Geschehen, keine Einleitung.
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
| `monster` | Hauptfigur und ein Monster, das näher kommt | `monster` (zombie, geist, schatten oder ein Emoji), `anzahl` (Zombies 1 bis 4), `ort`, `gefuehl`, `aktion` (zittert, rennt …), optional `text` |
| `titel` | Titelkarte einer Serie | `serie`, `teil`, `ort`, optional Figur mit `name` |
| `akte` | Ermittler-Wand mit roten Fäden und Lupe | `text` (Mitte), `punkte` (2 bis 4, Emoji oder kurzer Text) |
| `raetsel` | leuchtendes Fragezeichen, Lichtkegel, Nebel | `objekt`, optional `ort`, `text` |
| `karte` | alte Karte, Route bis zum X, Kompass | optional `objekt` (am X), `text` |

Zusätzlich für jede Szene: `wetter` (regen, nebel, blitz, schnee) und bei figur/zwei/gruppe/horror ein `monster` im Hintergrund.
Figuren können `name` (Namensschild) und `art` ("zombie", "blass") haben.

**Stimmung und Stimme:** Oben im Skript `"stimmung"`: `gruselig` (Horror), `mysterioes` (Rätsel, Mystery) oder
`neugierig` (lockere Erklärung). Gruselig und mysteriös bekommen unheimliche Musik (Brummen, Herzschlag, Spieluhr),
dunkleres Bild mit Nebel. Fehlt das Feld, ist Horror gruselig und alles andere mysteriös. Die Stimme (`klar`,
`erzaehler`, `unheimlich`) wählt die Zentrale passend zur Stimmung und lernt, welche am besten ankommt;
mit `"stimme"` im Skript ist sie fest.

**Serien:** Oben im Skript `"serie": "Station 13"` und `"teil": 1`, die Hauptfigur mit festem Namen und fester Farbe in `figur`. Erste Szene ist schon Action, die `titel`-Szene kommt als zweite, letzte Szene endet mit offener Frage ("Teil 2 kommt bald"). Vorbild: `seed/0110-horror-station-13-teil-1.json`.

- `ort`: strand, meer, stadt, wald, feld, nacht, haus, kinderzimmer, keller, schule (mit `tafel`: Text an der Tafel), buero, labor, weltall, wueste, burg, dorf, farbe, friedhof, spukhaus, krankenhaus, strasse (nachts), dunkelwald
- `gefuehl`: freude, angst, staunen, wut, traurig, denken, cool, neutral, k_o
- `aktion`: steht, zeigt, winkt, jubelt, rennt, zittert, denkt, faellt, schockiert, haende, schlurft, versteckt
- `farbe`: rot, blau, gelb, gruen, lila, navy · `hut`: keiner, bandana, matrose, kapitaen, krone, zylinder, helm, muetze, hexe, ritter
- `text` und `tafel` höchstens 22 Zeichen.
