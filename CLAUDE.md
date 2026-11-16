# Hinweise für Claude-Sitzungen in diesem Repo

## Täglicher Shorts-Nachschub: Mix seit 14.11.2026 (Julius' Entscheidung)

Diese Regel ist neuer als der Text der täglichen Skript-Aufgabe und gilt vor ihm.
Die Zahlen auf YouTube zeigen: Erklärvideos laufen deutlich besser als Einzel-Mystery
(Erklärvideos im Schnitt ca. 560 Aufrufe, Mystery seit 11.11. ca. 210).

Jeden Tag genau **15 Cartoon-Skripte** in `seed/` (seit 16.11.2026 abends, Julius' Wunsch):
**10 Strichmännchen** (ohne `welt`) und **5 Blockwelt** (`"welt": "block"`, 3D-Blockfiguren wie in einem
Bauklotz-Spiel, eigene Figuren, keine Marken). Gesendet wird jede volle Stunde von 8 bis 22 Uhr.

| Video-Typ | Strichmännchen (2D) | Blockwelt (3D) | zusammen |
|---|---|---|---|
| Erklärvideo „Was passiert, wenn …?“ (Du-Perspektive: Körper, Alltag, Extremfälle) | 4 | 2 | 6 |
| Erklärvideo „Warum …?“ (Alltagsfrage, überraschende Antwort) | 2 | 1 | 3 |
| Einzel-Mystery (echtes Rätsel, Titel „Das X, das niemand …“) | 2 | 1 | 3 |
| Horror (Einzelvideo) | 2 | 1 | 3 |
| **Summe** | **10** | **5** | **15** |

So hat jeder Video-Typ jeden Tag beide Looks, und der Vergleich 2D gegen 3D bleibt fair.
Vorbilder Erklärvideo: „Was passiert, wenn du tagelang nicht schläfst?“ (1.500 Aufrufe),
„Was passiert, wenn das Seil deines Aufzugs reißt?“ (940).

Bei 15 Themen am Tag besonders auf Doppelungen achten (vorher `seed/` und `docs/videos.json` prüfen).
Lieber ein schwächeres Thema weglassen als eins doppeln oder Fakten erfinden; dann mindestens die 5 Blockwelt-Videos schreiben.

`"vorrang": true` im Skript schiebt es in der Warteschlange ganz nach vorn (nur für „heute noch rausbringen“,
nicht in der täglichen Aufgabe benutzen).

- **Blockwelt-Horror:** ausgedachte Gruselgeschichten aus einer Spielwelt (leerer Server, Spieler ohne
  Namen, Chat-Nachrichten, Etage, die es nicht gibt …), `"chat"` in 2 bis 3 Szenen, Wendung am Ende.
  Vorbilder `seed/0199` bis `0201`.
- **Blockwelt-Mystery:** das echte Rätsel mit Blockfiguren nachgespielt (Fakten bleiben echt, nichts
  dazuerfinden), am Ende die offene Frage oder der überraschende Fund.
- **Blockwelt-Erklärvideo:** „du“ ist die Blockfigur. Meist Szenen `figur`, `zwei`, `gruppe`, `objekt`,
  `raetsel` (die werden 3D); höchstens eine 2D-Szene wie `vergleich` oder `akte`. Helle Orte
  (`feld`, `haus`, `buero`, `stadt`, `schule`, `labor`), `"stimmung": "neugierig"`, höchstens 1 bis 2
  kurze `"chat"`-Zeilen als Spiel-Gefühl. Aha-Moment am Schluss. Vorbild `seed/0205`.
- Gute Geschichte mit Wendung bzw. Aha-Moment ist bei allen Pflicht, egal welcher Look.
- Der erste Satz der Beschreibung enthält das Wort „Blockwelt“ (so erkennt man sie in `docs/videos.json`).
- Die Zentrale vergleicht unter „Was am besten funktioniert“ **„Look 2D/3D“** (`learn.world`) und,
  fairer, **„Look je Video-Typ“** (`learn.world_by_type`, z. B. „Horror · 3D“ gegen „Horror · 2D“),
  denn Erklärvideos heben sonst den Schnitt des Looks, in dem sie öfter laufen.
- Die Aufteilung 10 + 5 bleibt fest bis 30.11.2026. Danach je Video-Typ: Liegt ein Look in „Look je Video-Typ“
  bei mindestens 5 bewerteten Videos je Seite mehr als 30 % vorne, bekommt dieser Typ mehr von dem Look
  (der andere bleibt mit mindestens 1 pro Tag zum Gegentest). Bis Julius etwas anderes sagt.
- Keine Serien. Themen nicht doppeln (vorher `seed/` prüfen).
- Erster Satz = die krasse Situation oder Frage. Kein Intro, keine Begrüßung, ca. 22 s.

### Test: erzählte Geschichten mit warmer Stimme (seit 16.11.2026, Julius' Wunsch)

Julius mag ruhige „Storytime“-Videos mit freundlicher Stimme. Darum als Test, **ohne den Plan oben zu ändern**:
Montag, Mittwoch und Freitag wird **eins der 2 Strichmännchen-Mystery** zu einer erzählten Geschichte
(also 3 pro Woche, weiterhin 15 Shorts am Tag).

- Oben im Skript `"niche": "Erzählung"` (nicht „Geschichte“, so heißt die alte History-Nische) und `"stimmung": "warm"`.
  Dann wählt die App eine der warmen Stimmen (`freundlich`, `erzaehlerin`, `erzaehler`), ruhige Spieluhr-Musik
  und das helle Bild. Video-Typ in der Zentrale: „Erzählte Geschichte“.
- Ausgedachte Alltagsgeschichte in der Ich-Form (Familie, Nachbarn, Schule, Freunde), warm, mit Wendung am Schluss,
  die das Vorherige in neues Licht rückt. Keine echten Personen, nichts als „wahre Geschichte“ ausgeben;
  die Beschreibung beginnt mit „Eine ausgedachte Geschichte, ruhig erzählt:“. Keine Serien.
- „Ich“ am Anfang ist hier erlaubt (Hook-Prüfung kennt das). Erster Satz trotzdem die krasse Lage, höchstens 12 Wörter.
- Helle Orte (`haus`, `stadt`, `schule`, `dorf`, `feld`, `krankenhaus`), Szenen `figur`, `zwei`, `objekt`. 70 bis 85 Wörter.
- Vorbilder `seed/0208` bis `0210`. Läuft „Erzählte Geschichte“ nach 2 Wochen unter Video-Typ besser als Mystery,
  mehr davon vorschlagen (Julius fragen).

Die Stimme `freundlich` testet die App auch bei Erklärvideos mit (Stimme lernt unter „Was am besten funktioniert“).

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
