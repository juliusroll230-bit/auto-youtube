# Hinweise für Claude-Sitzungen in diesem Repo

## Täglicher Shorts-Nachschub: Mix seit 14.11.2026 (Julius' Entscheidung)

Diese Regel ist neuer als der Text der täglichen Skript-Aufgabe und gilt vor ihm.
Die Zahlen auf YouTube zeigen: Erklärvideos laufen deutlich besser als Einzel-Mystery
(Erklärvideos im Schnitt ca. 560 Aufrufe, Mystery seit 11.11. ca. 210).

Jeden Tag genau 5 Strichmännchen-Skripte in `seed/`:

- **3 Erklärvideos** (`"niche": "Erklären"`):
  - 2 im Muster „Was passiert, wenn …?“ in Du-Perspektive (Körper, Alltag, Extremfälle).
    Vorbilder: „Was passiert, wenn du tagelang nicht schläfst?“ (1.500 Aufrufe),
    „Was passiert, wenn das Seil deines Aufzugs reißt?“ (940).
  - 1 „Warum …?“-Alltagsfrage mit überraschender Antwort.
- **1 Einzel-Mystery** (echtes ungelöstes Rätsel, Titel „Das X, das niemand …“).
- **1 Horror** als Einzelvideo.
- **Vergleich 2D gegen 3D (seit 14.11.2026, Julius' Wunsch):** Von Mystery und Horror ist jeden Tag
  genau eins in der **Blockwelt** (`"welt": "block"`, 3D-Blockfiguren wie in einem Bauklotz-Spiel,
  eigene Figuren, keine Marken) und eins als **Strichmännchen** (ohne `welt`). An geraden Tagen ist
  Horror die Blockwelt, an ungeraden Mystery. Blockwelt-Horror sind ausgedachte Gruselgeschichten aus
  einer Spielwelt (leerer Server, Spieler ohne Namen, Chat-Nachrichten, Etage, die es nicht gibt …),
  mit `"chat"` in 2 bis 3 Szenen und einer Wendung am Ende; Vorbilder `seed/0199` bis `0201`.
  Der erste Satz der Beschreibung enthält das Wort „Blockwelt“ (so erkennt man sie in `docs/videos.json`).
- Die Zentrale vergleicht unter „Was am besten funktioniert“ das Merkmal **„Look 2D/3D“**
  (`learn.world`). Nach 7 Tagen mit je mindestens 5 bewerteten Videos: Liegt ein Look im Schnitt mehr als
  30 % vorne, bekommen Mystery und Horror beide diesen Look (der andere höchstens jeden 3. Tag zum Gegentest).
- Keine Serien. Themen nicht doppeln (vorher `seed/` prüfen).
- Erster Satz = die krasse Situation oder Frage. Kein Intro, keine Begrüßung, ca. 22 s.

Das lange Video (täglich 1, stärkstes Thema) bleibt wie bisher.

Die Zentrale vergleicht unter „Was am besten funktioniert“ den **Video-Typ**
(`learn.video_type`). Wenn Mystery dort wieder klar vorne liegt, den Mix zurückdrehen.

## Hook-Prüfliste und Humanizer (seit 14.11.2026)

Aus dem Skill-Paket „claude-content-skills“ (virality + humanizer) übernommen.
Für jedes neue Skript in `seed/` gilt vor dem Commit:

1. `python3 hookcheck.py seed/NEUE-DATEIEN.json --fix` ausführen.
   `--fix` entfernt Gedankenstriche, Begrüßungen und leere Ankündigungen.
2. Jeder Short soll **8/8** schaffen, mindestens 7/8. Was fehlt, steht als Tipp darunter.
   Die acht Punkte für die ersten 3 Sekunden:
   - startet sofort (kein „Hallo“, „Heute“, „In diesem Video“, „Wusstest du“),
   - erster Satz höchstens 12 Wörter (lange Videos 25),
   - Erklärvideo: „du“ oder die Frage im ersten Satz; sonst kein „Ich/Wir“ am Anfang,
   - Spannung im ersten Satz (plötzlich, niemand, verschwunden, eine Frage …),
   - erste Szene bewegt sich (`aktion` rennt/zittert/zeigt/schockiert, nicht „steht“),
   - erste Szene hat ein erkennbares Bild (`objekt`-Emoji oder `text`),
   - keine KI-Floskeln (siehe unten),
   - 40 bis 85 Wörter (ca. 22 s).
3. Humanizer beim Schreiben: Dinge direkt sagen. Nicht „nicht nur … sondern auch“,
   kein „faszinierend“, „spannend“, „unglaublich“, „atemberaubend“, „eintauchen“,
   „Reise durch“, „in der Welt der“, „es ist wichtig zu“, „letztendlich“,
   keine Gedankenstriche, keine Schlusszeile, die nur wiederholt. Keine erfundenen Zahlen.

Die App bereinigt neue Skripte beim Einlesen selbst noch einmal und zeigt die Note
in der Zentrale (Sendeplan und Zuschauer > „Hook-Prüfung“). Unter „Was am besten
funktioniert“ vergleicht sie „Hook-Prüfung“ stark / gut / schwach mit echten Aufrufen.

### Unslop-Regeln für Titel, Beschreibung und Thumbnail-Text (seit 15.11.2026)

Aus „unslop“ (Damir Sokolovsky, CC BY 4.0) die Text-Regeln übernommen und auf Deutsch umgebaut.
`hookcheck.py --fix` bereinigt jetzt auch `title`, `description` und `thumb_text`; Tipps dazu
stehen mit „·“ unter der Note (sie zählen nicht zur 8er-Note).

- Keine Hype-Wörter: „revolutionär“, „bahnbrechend“, „ultimativ“, „Game-Changer“, „unfassbar“,
  „du wirst nicht glauben“, „absoluter Wahnsinn“, „Gänsehaut garantiert“. Lieber sagen, was passiert.
- Kein KI-Deutsch: „heutzutage“, „spielt eine wichtige Rolle“, „von entscheidender Bedeutung“,
  „darüber hinaus“, „nicht zuletzt“, „zweifellos“, „Tatsächlich …“ am Satzanfang, „mehr als nur“, „Fakt ist:“.
- Keine unbelegten Behauptungen („99 % der Menschen …“, „die meisten wissen das nicht“,
  „wissenschaftlich bewiesen“ ohne Quelle).
- Titel: höchstens 1 Emoji, kein „!!“, nicht mehrere GROSSBUCHSTABEN-Wörter, kein Schlusspunkt,
  besser unter 60 Zeichen. Beschreibung ohne Begrüßung. Thumbnail-Text wiederholt nicht den Titel.

Nicht übernommen: `agent-reach` und `reel-analyzer` (laden fremde Videos), alles zu
Instagram-DMs, Leads und Werbung.

## Thumbnails (seit 15.11.2026)

Die App baut für jedes Video zwei eigene Thumbnails (`thumbnail.py`) und setzt eins beim Upload per API
(lange Videos 1280x720, Shorts 1080x1920). Welche Variante besser läuft, lernt sie unter „Was am besten funktioniert“
(„Thumbnail (lange Videos)“ / „Thumbnail (Shorts)“).

Jedes neue Skript in `seed/` (vor allem das lange Video) bekommt dafür das Feld
`"thumb_text": ["THEMA | Neugier-Zeile", "Satz für Variante B"]`:

- je Variante höchstens 4 Wörter, kurz und knallig, keine Wiederholung des Titels,
- A: links vom `|` das Thema in 1 bis 2 Wörtern (wird riesig), rechts die Neugier-Lücke
  (z. B. `"Kühlschrank | macht keine Kälte"`, `"Djatlow-Pass | bis heute ungelöst"`),
- B: eine Behauptung oder Frage, die man klären will (z. B. `"Er lügt dich an"`),
- keine Marken- oder Firmennamen, keine erfundenen Zahlen.

Fehlt das Feld, baut die App den Text aus dem Titel (Thema + Neugier-Zeile je Video-Typ).
