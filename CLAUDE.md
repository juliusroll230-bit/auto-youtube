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

Die App hält den Mix selbst (seit 18.11.2026): Von je 15 Shorts sind 5 Blockwelt (`block_per_day` in der Config,
Lernmodus wählt nur das Thema innerhalb des Looks). Weil ein Short auf dem Server ca. 1 Stunde rendert, rendert sie
in freien Minuten (auch nachts) bis zu 6 Shorts vor (`ready/`, Vorrat) und lädt zum Sendeplatz nur noch hoch.

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

### Mehr Gewinner-Themen (seit 20.11.2026, Julius' Wunsch)

Stand 19.11. (öffentliche Aufrufe): Der Kanal hängt fast überall bei ca. 1.000. Vorne liegen **Themen über den eigenen Körper
und Alltag in der Du-Perspektive**: „Was passiert, wenn du tagelang nicht schläfst?“ (2.600, mit Abstand vorn), Gänsehaut (1.500),
Luft anhalten (1.300), die eigene Stimme auf Aufnahmen (1.300), Schlüssel/Rätsel (1.100), Aufzug (1.000), Cent vom Wolkenkratzer (1.000).
Darum von den 15 Skripten am Tag **4 bis 5 Nachbarthemen der Gewinner** (zählen zu den Erklärvideo-Plätzen oben, kein Extra-Skript):

- Körper, Sinne, Gehirn und Schlaf, jeder kennt das Gefühl: Müdigkeit, Koffein, Hunger, Durst, Kälte, Hitze, Stille, Dunkelheit, Träume,
  Gähnen, Schluckauf, Gänsehaut, Schwindel, Zeitgefühl, Gedächtnis. Beispiele: „Was passiert, wenn du eine Woche nichts trinkst?“,
  „Warum bekommst du Schluckauf?“, „Was passiert, wenn du nie wieder träumst?“.
- Aus dem Titel der Top 10 jeweils ein **neues** Nachbarthema bauen (nicht dasselbe Thema nochmal): gleiche Art von Frage, anderer Körperteil,
  Sinn oder Extremfall.
- Die übrigen 10 bis 11 bleiben Vielfalt (Mystery, Horror, Technik, Natur, Geschichte), damit der Lernmodus weiter testen kann.
- Alle Regeln oben gelten weiter (Doppelungen prüfen, Fakten nicht erfinden, 2 bis 4 `*Schlüsselwörter*`, Auflösung im vorletzten Satz).
- Nach ca. 5 Tagen unter „Was am besten funktioniert“ prüfen, ob die Körper-Themen vorne liegen. Wenn nicht, wieder auf 2 am Tag zurück.

### Test: erzählte Geschichten mit warmer Stimme (seit 16.11.2026, Julius' Wunsch)

Julius mag ruhige „Storytime“-Videos mit freundlicher Stimme. Darum als Test, **ohne den Plan oben zu ändern**:
Montag, Mittwoch und Freitag wird ein Mystery zu einer erzählten Geschichte (3 pro Woche, weiterhin 15 Shorts am Tag),
in beiden Looks wie der Rest des Plans:
- **Montag: Strichmännchen** (statt eines der 2 Strichmännchen-Mystery),
- **Mittwoch: Blockwelt** (`"welt": "block"`, statt des Blockwelt-Mystery),
- **Freitag: abwechselnd**, in geraden Kalenderwochen Strichmännchen, in ungeraden Blockwelt.
Die Zentrale vergleicht das unter „Look je Video-Typ“ („Erzählte Geschichte · 2D“ gegen „· 3D“).

- Oben im Skript `"niche": "Erzählung"` (nicht „Geschichte“, so heißt die alte History-Nische) und `"stimmung": "warm"`.
  Dann wählt die App eine der warmen Stimmen (`freundlich`, `erzaehlerin`, `erzaehler`), ruhige Spieluhr-Musik
  und das helle Bild. Video-Typ in der Zentrale: „Erzählte Geschichte“.
- Ausgedachte Alltagsgeschichte in der Ich-Form (Familie, Nachbarn, Schule, Freunde), warm, mit Wendung am Schluss,
  die das Vorherige in neues Licht rückt. Keine echten Personen, nichts als „wahre Geschichte“ ausgeben;
  die Beschreibung beginnt mit „Eine ausgedachte Geschichte, ruhig erzählt:“. Keine Serien.
- „Ich“ am Anfang ist hier erlaubt (Hook-Prüfung kennt das). Erster Satz trotzdem die krasse Lage, höchstens 12 Wörter.
- Helle Orte (`haus`, `stadt`, `schule`, `dorf`, `feld`, `krankenhaus`), Szenen `figur`, `zwei`, `objekt`. 70 bis 85 Wörter.
- Blockwelt-Geschichte: „ich“ ist die Blockfigur, helle Orte (`haus`, `stadt`, `feld`, `dorf`, `schule`; `krankenhaus`
  und `strasse` sind in 3D nachts), gern 1 bis 2 kurze `"chat"`-Zeilen; erster Satz der Beschreibung mit „Blockwelt“.
- Vorbilder `seed/0208` bis `0210` (2D) und `seed/0259` (Blockwelt). Läuft „Erzählte Geschichte“ nach 2 Wochen unter Video-Typ besser als Mystery,
  mehr davon vorschlagen (Julius fragen).

### Test: Loop-Ende (seit 19.11.2026)

Stand 19.11.: Fast jeder Short bleibt bei ca. 800 bis 1.500 Aufrufen stehen (bester: Schlaf 2.600), egal ob
Erklärvideo, Mystery, Horror, 2D oder 3D. Das Thema ist also nicht die Grenze. YouTube zeigt jeden Short erst
einer kleinen Testgruppe und schiebt ihn nur weiter, wenn die Leute bis zum Ende schauen und nochmal schauen.
Darum als Test, **ohne den Plan oben zu ändern**: Jeden Tag bekommen **5 der 15 Skripte** `"ende": "loop"`:
2 „Was passiert, wenn“ (1× 2D, 1× 3D), 1 „Warum“ (2D), 1 Mystery (2D), 1 Horror (3D).

- Der letzte Satz endet offen, ohne Schlusspunkt, und der erste Satz vollendet ihn. Wer nicht aufpasst,
  merkt den Neustart nicht und schaut ein zweites Mal. Beispiele:
  - erster Satz „Was passiert, wenn du die Luft zu lange anhältst?“, letzter „Also frag dich beim nächsten Tauchen noch mal:“
  - erster Satz „Ein Schiff treibt im Atlantik, und niemand ist an Bord.“, letzter „Und bis heute weiß niemand, warum“
- Die Auflösung bzw. der Aha-Moment kommt im vorletzten Satz. Kein Abschiedssatz, kein „Abonnier“.
- Loop-Skripte eher kurz: 45 bis 65 Wörter (ca. 16 bis 20 s).
- `hookcheck.py` gibt einen Tipp mit „·“, wenn der letzte Satz mit Punkt endet.
- Die Zentrale vergleicht unter „Was am besten funktioniert“ **„Ende (Loop)“** (`learn.ending`).
  Liegt „Loop“ nach mindestens 10 bewerteten Videos je Seite klar vorne, Julius vorschlagen, alle Shorts so zu bauen.

### Test: Soundeffekte und Bild-Effekte (seit 19.11.2026)

Die App entscheidet selbst, welche von drei Stufen ein Cartoon-Short bekommt (`look.effekte`, Lernmerkmal „Soundeffekte“,
`learn.choose_effects`, danach 3 von 4 die beste Stufe):

- **dezent:** wie bisher, Whoosh bei Schnitten, Klick bei Zahlen.
- **stark:** vor dem **vorletzten Satz** steigt ein Riser an, dann harter Schnitt, Schlag, kurze Musikpause, Bild-Stoß mit Aufblitzen.
- **voll:** wie stark, dazu steigender Ton und kurzer Zoom auf jedem `*Schlüsselwort*`, langsamer Kamera-Zug in jeder Szene
  und ein Reaktions-Sticker (🤯 neugierig, 😱 gruselig, 🤔 mysteriös, 🥹 warm) mit Glockenton auf der Auflösung.
  Im Skript optional `"sticker": "🤯"` für ein eigenes Emoji.

Darum in **jedem** Skript: der vorletzte Satz ist die Auflösung bzw. der Aha-Moment, und **2 bis 4 Wörter** stehen
in `*Sternchen*` (die wichtigsten, nicht mehr als eins pro Satz). Alles wird selbst erzeugt (`audio.py`, Emoji-Schrift im Repo),
keine fremden Sounds, Memes oder Bilder.

Die Stimme `aufgeregt` (seit 19.11.2026, Julius: „die Stimme ist so trocken“) ist bei Erklärvideos die erste Wahl: Thorsten-emotional (Sprecher „amused“), etwas flotter, aber **gleichmäßig und gut verständlich**. Julius hat sie am 19.11. mehrfach korrigiert (zu extrem, zu hoch wie Stimmbruch, nicht so hoch und runter, kein Absenken am Satzende), deshalb: tiefere Grundlage (`BASE`), niedriges Rauschen (`VOICE_NOISE`), Satz am Stück, keine Melodie-Tricks mehr (`make_short.speak_lively`), ohne Hall. Lange Videos bekommen immer die Stimme `klar` (Julius mag sie zum Erklären). Darum die Schlüsselwörter in jedem Skript setzen. Die Stimme `freundlich` testet die App auch bei Erklärvideos mit (Stimme lernt unter „Was am besten funktioniert“).

Das lange Video (täglich 1, stärkstes Thema) bleibt wie bisher.

Die Zentrale vergleicht unter „Was am besten funktioniert“ den **Video-Typ**
(`learn.video_type`). Wenn Mystery dort wieder klar vorne liegt, den Mix zurückdrehen.

### Test: Spannung und lange Entspannungsvideos (seit 20.11.2026)

Julius fragte nach Feuer-/Regen-, Spannungs- und Lern-Videos. **Kein Split-Screen in Shorts** (Julius, 20.11.2026) und
keine reinen Feuer-/Regen-Shorts (YouTube wertet sie leicht als wiederholte Inhalte). Stattdessen:

- **Spannung (Shorts):** 1 von 15 Cartoon-Shorts bekommt einen leisen Herzschlag, der bis zur Auflösung schneller wird
  (`audio.tension_beats`), roten Puls am Rand und einen Countdown oben links (`learn.choose_layout`, `look.aufbau`).
  Die App wählt selbst, die tägliche Skript-Aufgabe ändert sich nicht (zum Ausprobieren im Skript `"aufbau": "spannung"`).
  Läuft sie nach mind. 5 Videos je Seite mehr als 30 % vor „normal“ („Spannung (Herzschlag)“ unter „Was am besten funktioniert“),
  bekommt sie 2 Plätze mehr.
- **Lange Entspannungsvideos:** `entspannung.py` baut Lagerfeuer, Regen am Fenster oder Pendel-Welle als nahtlose Schleife,
  z. B. 1 Stunde (`python entspannung.py feuer 60 ordner`), komplett selbst gezeichnet und vertont (`cartoon/web/ambient.js`,
  `audio.ambience`). Gehört auf einen **eigenen Kanal**, nicht auf „60 Sekunden Wissen“. Keine fremden Clips oder Musik.

- **Entspannungskanal (seit 20.11.2026, Julius' Wunsch):** dritter YouTube-Kanal, in der Zentrale unter Kanäle verbinden
  (`relax_token`, wie Clipi). `server.relax_worker` baut täglich ab `relax_hour` (Standard 17 Uhr) ein Video von `relax_minutes`
  (Standard 120) und lädt es hoch, Art reihum Feuer, Regen, Pendel. Keine Skripte dafür schreiben, die tägliche Aufgabe bleibt gleich.

### Vorbilder (seit 20.11.2026, Julius' Wunsch)

`vorbilder.py` hat 14 erfolgreiche Kanäle in unseren Nischen (Zack D. Films, What If, Unlucky Guy, SONNENSEITE …).
Die Zentrale (Karte „Vorbilder“ im Reiter Zuschauer) und GitHub Actions (`docs/vorbilder.json`, alle 12 Stunden)
lesen selbst Titel und Aufrufe ihrer neuesten Videos. Für die tägliche Skript-Aufgabe:

- Vor dem Schreiben `docs/vorbilder.json` lesen: `trend` (was gerade schnell Aufrufe sammelt), `muster` gegen `unsere`
  (Titelbau) und `tips`. Die Tipps zum Titel gelten für die neuen Skripte.
- Von den 15 Skripten **2 „Vorbild-Ideen“**: die **Art** einer Trend-Frage nehmen und ein **eigenes** Thema daraus machen
  (z. B. Trend „How Stitches Work“ → eigenes Körper-Thema wie „Warum juckt eine Wunde beim Heilen?“). Zählen zu den Plätzen oben.
- Nie ein Thema, einen Titel, Text oder ein Bild 1:1 übernehmen, keine Marken oder fremden Figuren, keine fremden Videos clippen.
  Fakten wie immer selbst prüfen.
- Muster aus der Recherche (20.11.2026): Titel 3 bis 6 Wörter plus höchstens 1 Emoji am Ende, eine Frage zu etwas,
  das jeder kennt (Körper, Gegenstand zu Hause); Blockwelt-Horror als Regel oder Countdown
  („Geh nachts nie zum Eiswagen“, „Du hast 60 Sekunden, um …“) an vertrauten Orten (Schule, Bus, Supermarkt);
  ab und zu ein Mitmach-Hook („Teste dich: …“) oder eine Wahl-Frage („Welche Tür würdest du nehmen?“).

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
