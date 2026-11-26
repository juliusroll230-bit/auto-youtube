# Hinweise für Claude-Sitzungen in diesem Repo

## Täglicher Shorts-Nachschub: Mix seit 14.11.2026 (Julius' Entscheidung)

Diese Regel ist neuer als der Text der täglichen Skript-Aufgabe und gilt vor ihm.
Die Zahlen auf YouTube zeigen: Erklärvideos laufen deutlich besser als Einzel-Mystery
(Erklärvideos im Schnitt ca. 560 Aufrufe, Mystery seit 11.11. ca. 210).

## Wieder 15 Shorts am Tag (seit 25.11.2026, Julius' Entscheidung)

Julius will wieder **15 Shorts am Tag plus das lange Video** auf dem Hauptkanal: **10 Strichmännchen und 5 Blockwelt**
(`block_per_day` 5, `max_shorts_day` 15, Sendezeiten jede volle Stunde 8 bis 22 Uhr, `hours_v10`). Das ersetzt die 8-Skripte-Regel vom 23.11.
Zur Einordnung (ehrlich): Die Auswertung vom 20. bis 22.11. zeigte, dass Uploads ab dem 11. am Tag kaum Aufrufe bekamen (0 bis 3).
Die Zentrale vergleicht das weiter („Was am besten funktioniert“); Ende Dezember mit Julius die Zahlen ansehen.

Jeden Tag genau **15 Cartoon-Skripte** in `seed/`:

| Typ | Strichmännchen | Blockwelt | zusammen |
|---|---|---|---|
| Körper/Alltag-Erklärvideos („Was passiert, wenn du …?“ / „Warum …?“, Du-Perspektive, inkl. Aktuell-Skript) | 4 | 2 | 6 |
| Erzählte Geschichten (`"niche": "Erzählung"`, warm, siehe unten) | 2 | 1 | 3 |
| Mystery | 2 | 1 | 3 |
| Horror | 1 | 1 | 2 |
| Vielfalt (Technik, Natur, Geschichte) | 1 | 0 | 1 |
| **Summe** | **10** | **5** | **15** |

Seit 26.11.2026 (Julius: „wäre besser, davon mehr zu probieren“, weil der meistgesehene Short eine erzählte Geschichte ist,
„Warum Mama mir zwei Brote einpackt“, 2.800 Aufrufe): **jeden Tag 3 erzählte Geschichten** (2 Strichmännchen + 1 Blockwelt),
dafür 1 Erklärvideo weniger (das Aktuell-Skript zählt zu den 4 Strichmännchen-Erklärvideos).

Loop-Ende (siehe unten) bekommen 5 der 15 (2 Erklärvideos, 1 Warum, 1 Mystery, 1 Horror).

### Aktuell-Skript (seit 23.11.2026, Julius' Wunsch nach dem Video „20 NEW Faceless YouTube Niches“)

Das Video (One Person Business, Verkaufsvideo für eine Community, Einkommenszahlen nicht überprüfbar) nennt als wiederkehrende Muster:
Kanäle explodieren, wenn sie **auf aktuelle Nachrichten aufspringen**, **Was-wäre-wenn-/Survival-/Geschichts-Erklärer**
mit Animation machen, und **den deutschsprachigen Markt** bedienen (weniger Konkurrenz). Nicht kopieren, nur Muster nehmen. Darum:

- 1 von 15 Skripten pro Tag greift ein **aktuelles Ereignis dieser Woche** auf (Wissenschaft, Natur, Raumfahrt, Technik, Gesundheit, Wetter,
  Rekorde; keine Politik, keine Vorwürfe gegen echte Personen, keine Tragödien mit Toten). Vor dem Schreiben mit der Web-Suche
  **zwei unabhängige Quellen** prüfen, nur belegte Fakten verwenden, keine erfundenen Zahlen.
- Aufbau: Frage in Du-Perspektive zum Ereignis, Auflösung im vorletzten Satz.
  Im Skript `"aktuell": true` setzen (Lernmerkmal „Aktuelles Thema“ in der Zentrale vergleicht mit „zeitlos“).
- Titel mit dem Ereignis im Kern, aber ohne Clickbait-Lüge. Nach 10 Videos je Seite schauen, ob „aktuell“ klar vorn liegt, dann mehr davon.

Bei 15 Themen am Tag besonders auf Doppelungen achten (nie dasselbe Skript zweimal: am 21.11. lief „Der Schulbus …“ doppelt, das zweite bekam 1 Aufruf) (vorher `seed/` und `docs/videos.json` prüfen).
Lieber ein schwächeres Thema weglassen als eins doppeln oder Fakten erfinden; dann mindestens die 5 Blockwelt-Videos schreiben.

Die App hält den Mix selbst (seit 18.11.2026): Seit 25.11. sind wieder von 15 Shorts am Tag 5 Blockwelt (`block_per_day` in der Config,
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

Julius mag ruhige „Storytime“-Videos mit freundlicher Stimme. Seit 26.11.2026 nicht mehr nur Montag, Mittwoch und Freitag,
sondern **jeden Tag 3** (siehe Tabelle oben): **2 Strichmännchen und 1 Blockwelt** (`"welt": "block"`).
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
- Vorbilder `seed/0208` bis `0210` (2D) und `seed/0259` (Blockwelt). Läuft „Erzählte Geschichte“ ca. 10.12. unter Video-Typ besser als Mystery,
  Julius vorschlagen, noch 1 Mystery dafür zu tauschen; läuft sie klar schlechter, zurück auf 2 am Tag.
- Bei 3 Geschichten am Tag besonders auf Abwechslung achten (Ort, Figur, Wendung), nie dieselbe Schablone
  (immer „Plötzlich liegt jeden Morgen …“ wäre Massenware). `hookcheck.py` meldet gleiche Einstiege mit „·“.

### Test: Loop-Ende (seit 19.11.2026)

Stand 19.11.: Fast jeder Short bleibt bei ca. 800 bis 1.500 Aufrufen stehen (bester: Schlaf 2.600), egal ob
Erklärvideo, Mystery, Horror, 2D oder 3D. Das Thema ist also nicht die Grenze. YouTube zeigt jeden Short erst
einer kleinen Testgruppe und schiebt ihn nur weiter, wenn die Leute bis zum Ende schauen und nochmal schauen.
Darum als Test: Jeden Tag bekommen **5 der 15 Skripte** (seit 25.11. wieder, am 23.11. waren es 3 der 8) `"ende": "loop"`:
2 Erklärvideos (1× 2D, 1× 3D), 1 Warum (2D), 1 Mystery (2D), 1 Horror (3D).

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

- **Quiet Corner (seit 21.11.2026, Julius: „übernimm du alles“):** Der Entspannungskanal heißt „Quiet Corner“ und läuft
  komplett von selbst (`entspannung.py`, Szenen in `cartoon/web/quiet.js`, Klang `audio.soundscape`, Reiter „Quiet Corner“ `#ruhe`).
  15 Ideen in 5 Szenen (Regen-Zimmer, Kamin-Ecke, Café bei Nacht, Fantasy-Bibliothek, Lagerfeuer im Wald), immer mit Pflanzen,
  3 bis 10 Stunden, 2 am Tag (ab 6 und 17 Uhr, Julius 21.11.: „mehr und länger“), Titel nach dem Muster der großen Ambience-Kanäle
  (Bild + Emoji + Suchbegriff + Zweck | Dauer), Tags mit Suchbegriffen je Szene (`KEYWORDS`), Englisch, ruhig, ohne Kitsch, Thumbnail höchstens 3 Wörter, nach jedem langen Video ein
  30-s-Teaser-Short. Lernmodus wählt Szene und Länge nach Aufrufen pro Tag. Neue Ideen nur als Eintrag in `IDEAS` (eigene Zeichnung,
  eigener Klang), keine fremden Clips, Musik oder Marken. Banner/Profilbild: `python entspannung.py branding ordner` (Varianten A/B/C).

### Test: Tempo „schnell“ (seit 21.11.2026, Julius' Wunsch nach zwei Instagram-Reels)

Julius mag schnelle Reels (3D-Sketch und Tipp-Liste, je ca. 22 bis 25 s). Darum als Test, **ohne den Plan oben zu ändern**:
Die App wählt selbst **2 von 15 Cartoon-Shorts** (`learn.choose_tempo`, `look.tempo`, Lernmerkmal „Tempo (schnell)“):
Schnitt alle ca. 1,3 s (`make_short.fast_cuts`) mit wechselnder Einstellung (weit, nah, schräg), Stoß-Zoom und kurzem Blitz,
selbst erzeugter Snap-Ton (`audio.snap`), immer die klare Stimme in normalem Tempo mit kurzen Pausen (Julius 21.11.: „die Stimme muss klarer sein“), Musik leiser, große Wort-für-Wort-Untertitel
(Schlüsselwörter gelb) und gelber Fortschrittsbalken oben. Nicht zusammen mit „Spannung“, nie bei langen Videos.
Zum Ausprobieren im Skript `"tempo": "schnell"`.

- Die tägliche Skript-Aufgabe ändert sich nicht. Weil jeder Short dran kommen kann: kurze Sätze (5 bis 10 Wörter) helfen allen Shorts.
- Liegt „schnell“ nach mind. 5 bewerteten Videos je Seite mehr als 30 % vorn, bekommt es 4 Plätze mehr (6 von 15).
  Dann Julius vorschlagen, ob alle Shorts so laufen sollen.
- Nur Stil gelernt (Tempo, Schnitt, Untertitel), nichts aus den Reels übernommen.

### Test: Abo-Aufruf am Ende (seit 22.11.2026, Julius will mehr Abos)

Die App hängt selbst einen kurzen Abo-Aufruf an die Cartoon-Shorts (nicht lange Videos, nicht Firmen-Spiel, Clipi oder Quiet Corner).
Drei Varianten reihum (`learn.choose_abo`, `store.next_abo`, `look.abo`, Lernmerkmal „Abo-Aufruf“):

- **gesprochen:** nach dem letzten Satz sagt die Stimme einen Satz wie „Folge für das nächste Rätsel.“ (ca. 2 s), dazu ein Abo-Knopf
  mit Glocke im Bild, leiser Klick und Glockenton.
- **eingeblendet:** nur der Knopf, ca. 2,6 s vor Schluss während des letzten Satzes. Loop-Shorts bekommen nie „gesprochen“
  (der Satz würde den Loop zerstören), dort blendet der Knopf kurz vor dem Ende aus.
- **ohne:** Gegentest.

Die Sätze stehen in `learn.ABO_LINES` je Video-Typ und wechseln reihum (Merkmal „Abo-Aufruf (Satz)“). Neue Sätze nur dort eintragen:
höchstens 6 Wörter, ehrlich (keine „Teil 2“-Versprechen, es gibt keine Serien), keine Floskeln, keine Gedankenstriche.
Gelernt wird nach **neuen Abos pro 1.000 Aufrufe** (YouTube Analytics `subscribersGained`): Haben alle Varianten mind. 5 Videos
mit Abo-Zahlen, bekommt die beste 3 von 4 Shorts. Die Zentrale zeigt die Zahl unter „Was am besten funktioniert“.

- Die tägliche Skript-Aufgabe ändert sich **nicht**: Skripte enthalten weiterhin **keinen** Abo-Satz und kein „Abonnier“
  (das macht die App). Zum Ausprobieren im Skript `"abo": "gesprochen"` / `"eingeblendet"` / `"ohne"`.
- Ca. 1.12. prüfen: Bringt „gesprochen“ oder „eingeblendet“ klar mehr Abos pro 1.000 Aufrufe, ohne dass „Ø angesehen“ fällt,
  Julius vorschlagen, „ohne“ wegzulassen.

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

### Vorbild-Taktiken und besseres Lernsystem (seit 25.11.2026, Julius' Wunsch)

Julius: „Taktiken der anderen Kanäle übernehmen, Musik und Stimme anpassen, coolere Übergänge, mehr was die Leute dranhält,
Lernsystem verbessern, auch bei Quiet Corner.“ Was bei mehreren Vorbildern gleich ist, steht in `vorbilder.TAKTIKEN`
(Karte „Vorbilder“ zeigt dazu den Stand bei uns). Nichts wird fest eingebaut: die App testet jede Taktik als Variante
und der Lernmodus nimmt nur, was bei unseren Zuschauern besser läuft. Alles selbst erzeugt, keine fremde Musik.

- **Musik** (`look.musik`, `learn.MUSIC_FOR_MOOD`, `audio.tension_music`/`light_music`/`drop_music`): Erklärvideos
  „beat“ (bisher), „spannung“ (pulsierend mit Ticken), „leicht“ (verspieltes Zupfen), „drop“ (Beat setzt erst auf dem Aha-Moment ein);
  Mystery „dunkel“ oder „spannung“; Horror bleibt dunkel, Geschichten warm.
- **Übergang (Cartoon)** (`look.uebergang`, `learn.CARTOON_TRANSITIONS`, `cartoon/web/main.js` trOverlay): „whip“ (bisher), „zoom“,
  „wisch“ (flüssiger Farb-Wisch), „kreis“, „blitz“. Bei Tempo „schnell“ gibt es nur harte Schnitte.
- **Dranbleiben** (`look.halten`, `learn.HOLDS`): „frage“ (Titel-Frage oben bis zur Auflösung, dann grüner Haken), „balken“
  (Fortschrittsbalken), „beides“, „ohne“. Darum: **Titel als echte Frage** formulieren, wo es passt, höchstens ca. 50 Zeichen.
- Zum Ausprobieren im Skript `"musik"`, `"uebergang"`, `"halten"` (nicht in der täglichen Aufgabe benutzen).
- **Lernsystem** (`learn.relative`, `learn.thompson`, `learn.chances`): Jedes Video wird mit den Videos aus ±4 Tagen verglichen
  (Faktor „1,3× Schnitt“), gerechnet im Logarithmus (Ausreißer ziehen nicht allein), Videos von vor 3 Wochen zählen halb.
  Statt fest 3 von 4 wählt das Thompson-Verfahren: sicherer Gewinner fast immer, knappe Rennen werden weiter getestet.
  Die Zentrale zeigt „% sicher“. Nur zum Ansehen: „Upload des Tages“ (1. bis 5. / 6. bis 10. / 11. bis 15.) und „Uhrzeit“.
- **Quiet Corner** (`entspannung.belief`, `_pick`, `learn_rows`, `use_story`): Szene und Länge mit derselben Methode
  (jedes 8. Video testet trotzdem), dazu Vergleich „Geschichte oder nur Szene“ und „Uhrzeit“. Laufen reine Szenen nach
  mindestens 4 Videos je Seite zu 80 % sicher besser, kommt die Geschichte nur noch in jedem 2. Video (die tägliche Geschichte
  trotzdem schreiben, sie wird dann eben später gesendet).
- Ca. 10.12. unter „Was am besten funktioniert“ ansehen und Julius sagen, welche Taktiken bei uns gewinnen.

### Nischen-Kompass, Titel-Muster und Zwischen-Haken (seit 25.11.2026, Julius' zweites „claude-content-skills“-Paket)

Das Paket (Ootto, MIT, jetzt ca. 60 Skills, fast alles für Instagram) wurde nochmal ausgewertet. Übernommen nur, was zu
unserem Kanal passt (`nische.py`): **hook-mining** (Titel nach Muster sortieren und an echten Aufrufen messen, nie kopieren),
**going-viral** (Zwischen-Haken in der Mitte, Einstieg nicht immer gleich) und **content-audit** (stärkstes Themenfeld finden).
Nicht übernommen: agent-reach/reel-analyzer (laden fremde Videos), alles zu DMs, Leads, Werbung, Karussells, LinkedIn/X, UGC.

- Die Zentrale lernt drei neue Merkmale, aus dem Skript berechnet, also sofort auch für alle alten Shorts:
  **„Themenfeld“** (`learn.features` → `nische.topic_field`: Körper & Sinne, Weltall, Natur & Erde, Tiere, Technik & Alltag,
  Echte Rätsel & Geschichte, Grusel, Alltagsgeschichte …), **„Titel-Muster“** (`nische.title_pattern`: Was passiert, wenn …? /
  Warum …? / Das X, das niemand … / Regel/Countdown / Mitmachen/Wahl / Zahl/Liste / Mythos/Irrtum / Ich-Geschichte …) und
  **„Zwischen-Haken (Mitte)“** (`nische.rehook`: mit/ohne). Karte **„Nischen-Kompass“** im Reiter Zuschauer zeigt Bestes und
  Schwächstes je Gruppe mit ehrlichen Hinweisen (auch, wenn Upload 11 bis 15 klar schwächer läuft).
- GitHub Actions schreibt alle 3 Stunden `docs/nische.json` (`tools/nische_feed.py`, öffentliche Aufrufe nach ca. 1 Tag,
  gesammelt in `docs/statistik.json`). **Vor dem Schreiben der täglichen Skripte `docs/nische.json` lesen:** Liegt ein
  Themenfeld oder Titel-Muster mit mindestens 5 Videos klar vorn (Faktor ≥ 1,3), bei den freien Plätzen (Vielfalt,
  Vorbild-Ideen, Mystery-Themen) dieses Feld/Muster bevorzugen; das schwächste seltener. Der feste Mix oben bleibt.
- **Zwischen-Haken (Test):** In ungefähr **der Hälfte** der Shorts nach ca. einem Drittel ein Satz, der neu anzieht
  („Aber dann …“, „Doch das Seltsamste …“, „Und genau da …“), die andere Hälfte ohne, damit die Zentrale vergleichen kann.
  Kein leerer Füllsatz, er muss eine echte neue Wendung bringen. `hookcheck.py` gibt dazu einen Tipp mit „·“.
- **Vielfalt beim Einstieg:** `hookcheck.py` vergleicht neue Skripte mit den letzten 40 in `seed/` und meldet mit „·“,
  wenn zu viele gleich anfangen (Stand 25.11.: „Plötzlich …“ in 10 der letzten 60) oder zu viele Titel „Das X, das niemand …“
  bzw. „niemand“ enthalten. Dann umschreiben (Regel, Zahl, Frage, mitten in der Handlung). Fragen-Einstiege bei Erklärvideos
  („Was passiert, wenn du …?“) sind das Format und zählen nicht. Grund: YouTubes Regel gegen Massenware (07.2026).
- Neue Muster oder Felder nur in `nische.PATTERNS` / `nische.FIELDS` eintragen. Test: `tests/nische_test.py`.

### Gewinner nachbauen, Frage-Kommentar, Geschichten-Playlist (seit 26.11.2026, Julius' Wunsch)

Der meistgesehene Short ist die erzählte Geschichte „Warum Mama mir zwei Brote einpackt“ (`seed/0234`, 2.800 Aufrufe),
danach „Was passiert, wenn du tagelang nicht schläfst?“ (2.600). Darum baut die tägliche Aufgabe Gewinner nach:

- **Vor dem Schreiben** `docs/nische.json` → `gewinner` lesen (meistgesehene Shorts je Video-Typ mit Skript-Datei,
  öffentliche Aufrufe nach ca. 1 Tag). Die Zentrale zeigt dieselbe Liste genauer (Reiter Zuschauer > „Mehr Videos am Stück“).
  Steht dort noch nichts Besseres, gelten die beiden oben.
- **Jeden Tag 3 Nachbauten**, die zu den Plätzen der Tabelle oben zählen (kein Extra-Skript, der Mix bleibt):
  **2 der 3 erzählten Geschichten** nach dem Aufbau der besten Geschichte und **1 Erklärvideo** nach dem Aufbau des besten Erklärvideos.
- „Gleicher Aufbau“ heißt: dieselbe Art von Titel (z. B. „Warum Mama mir …“ → „Warum Opa jeden Abend …“), derselbe Rhythmus
  (kleines Rätsel im Alltag, das sich jeden Tag wiederholt, ein unauffälliges Detail in der Mitte, Wendung im vorletzten Satz, die alles
  in warmes Licht rückt), ähnliche Länge und Szenenfolge. **Neue** Figuren, neuer Ort, neues Rätsel und neue Wendung. Nie dieselbe
  Geschichte mit anderen Namen (YouTubes Regel gegen Massenware), nicht beide Nachbauten des Tages mit derselben Wendung.
- Im Skript `"nachbau": "<slug des Gewinners>"` setzen (z. B. `"geschichte-zwei-brote"`). Lernmerkmal „Gewinner-Nachbau“ unter
  „Was am besten funktioniert“. Liegt „Gewinner nachgebaut“ ca. 10.12. bei mind. 5 Videos je Seite klar vorn, Julius vorschlagen, mehr davon.
- **Frage-Kommentar:** Die App schreibt kurz nach jedem Upload selbst einen Kommentar mit einer Frage (`binge.py`, reihum je Video-Typ).
  Besser ist eine Frage, die genau zum Video passt: in **jedem** Skript `"frage"` setzen, eine Zeile, höchstens ca. 80 Zeichen,
  echte Frage an die Zuschauer, die man in einem Satz beantworten kann (Geschichte: „Wem hättest du das zweite Brot gegeben?“,
  Horror: „Hättest du dich umgedreht?“, Mystery: „Was glaubst du, war es?“, Erklärvideo: „Wie lange warst du schon mal wach?“).
  Kein Link, kein „Abonnier“, kein Gedankenstrich, höchstens 1 Emoji, nichts, was die Auflösung verrät. Anpinnen geht per API nicht.
- **Geschichten-Playlist:** Jede erzählte Geschichte kommt von selbst in die Playlist „Ruhige Geschichten zum Zuhören“, die
  meistgesehenen oben, Playlist auch als Abschnitt auf der Kanalseite. Ehrlich bleiben: kein „Teil 2“, keine Serien (siehe oben).
  Die Skripte ändern sich dafür nicht.

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

## Quiet Corner: Einschlaf-Geschichten (seit 24.11.2026, Julius' Entscheidung)

Nach der Nischen-Recherche (Einschlaf-Geschichten: wenig Konkurrenz, 5 bis 12 $ pro 1.000 Aufrufe, ruhiges Hören über lange Zeit)
liest Quiet Corner jetzt eine **ausgedachte englische Geschichte** vor (`sleepstory.py`, Stimme `en_GB-northern_english_male-medium`,
Julius hat sie am 24.11. aus 4 Hörproben gewählt). Darunter läuft leise die Szene, danach weiter bis zur vollen Stunde.
Gibt es keine neue Geschichte, läuft wie bisher nur die Szene (`relax_stories` in der Config, Standard an).

- Für die tägliche Aufgabe: **eine neue Geschichte pro Tag** als `sleep/NNNN-kurzer-name.json` (nächste freie Nummer), Felder
  `id` (= Dateiname ohne .json), `title` (Englisch, 2 bis 6 Wörter), `thumb` (höchstens 3 Wörter), `scene` (eine aus `entspannung.SCENES`:
  regenzimmer, kamin, cafe, bibliothek, lagerfeuer), `about` (ein Satz, „An invented story about …. Not a true story.“), `text`.
- Text: Englisch, 2.500 bis 4.000 Wörter (ca. 25 bis 40 Minuten Sprache), Absätze mit Leerzeile, ruhig und gleichmäßig.
  Anfang: kurzes Willkommen und 2 Atemsätze. Mitte: langsame Bilder, keine Handlung mit Spannung, keine Cliffhanger, kein Streit.
  Ende: die Figur schlafen legen, dann direkt zu den Hörern („You can rest now.“) und „Goodnight.“
- **Jede Geschichte anders** (Ort, Figur, Jahreszeit, Rhythmus), nie dieselbe Schablone mit anderem Namen, sonst greift YouTubes Regel gegen
  Massenware (Stand 07.2026, „inauthentic content“). Vorher `sleep/` ansehen.
- Keine Ratschläge zu Gesundheit, Geld oder Recht, keine echten Personen, nichts als „wahre Geschichte“ ausgeben.
  Fakten (z. B. Geschichte eines Ortes) müssen stimmen, sonst nichts behaupten.
- Die Beschreibung weist selbst darauf hin, dass die Stimme synthetisch und die Geschichte ausgedacht ist (`sleepstory.DISCLOSURE`).
- Nach ca. 2 Wochen Zahlen ansehen (Aufrufe pro Tag, Wiedergabezeit). Wenn nicht besser als die reinen Szenen, wieder mehr Szenen.

### Quiet Corner: Lernmodus (seit 25.11.2026)

Die Zentrale lernt bei Quiet Corner jetzt aus den Aufrufen pro Tag (nur Aufrufe, keine Wiedergabezeit): Szene, Länge, **Titel-Stil**
(`klassisch`, `dauer`, `suche`), **Vorschaubild-Stil** (`links`, `mitte`), **Klang** (`klar`, `weich`) (Uhrzeit und Geschichte-oder-Szene lernt `learn_rows` ebenfalls).
Jede Option wird erst probiert, danach bekommt die beste 3 von 4 Videos (`entspannung.choose_style`). Anzeige im Reiter Quiet Corner unter „Was am besten läuft“.
Neue Stile nur in `entspannung.TITLE_STYLES` / `THUMB_STYLES` / `SOUND_STYLES` eintragen. Test: `tests/style_test.py`.

Teaser (Julius 25.11.2026: „immer Teaser“): Zu jedem langen Quiet-Corner-Video wird immer ein Teaser-Short gebaut (unabhängig von `relax_shorts`).
Klappt der Upload nicht, gibt es 3 Versuche, danach liegt er in `relax-teasers/` und `relax_retry_teasers` holt ihn bei der nächsten Prüfung nach. Test: `tests/teaser_test.py`.
