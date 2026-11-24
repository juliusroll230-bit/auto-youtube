# Hinweise für Claude-Sitzungen in diesem Repo

## Täglicher Shorts-Nachschub: Mix seit 14.11.2026 (Julius' Entscheidung)

Diese Regel ist neuer als der Text der täglichen Skript-Aufgabe und gilt vor ihm.
Die Zahlen auf YouTube zeigen: Erklärvideos laufen deutlich besser als Einzel-Mystery
(Erklärvideos im Schnitt ca. 560 Aufrufe, Mystery seit 11.11. ca. 210).

## Wichtig seit 23.11.2026: nur noch 8 Skripte am Tag (Aufrufe-Einbruch, Julius' Auftrag „über 10.000 Aufrufe“)

Auswertung 20. bis 22.11. (Aufrufe nach 4 bis 5 Stunden): Der **1. bis 10. Upload eines Tages** bekam ca. 450 bis 900 Aufrufe,
**jeder Upload ab dem 11. am Tag 0 bis 3**, egal ob Strichmännchen, Blockwelt, Firmen-Folge oder lang (genau an 3 Tagen hintereinander).
Mit 15 Shorts plus Firma plus lang waren das 17 Uploads, also gingen ca. 40 % der Videos ins Leere. Darum:

- Jeden Tag genau **8 Cartoon-Skripte** in `seed/` (App sendet 7 Shorts, 1 Reserve; dazu Firmen-Folge und langes Video = 9 Uploads).
  Gesendet wird Mo bis Fr 12, 14, 15, 16, 17, 18, 19 Uhr, Sa/So 11, 13, 15, 16, 17, 18, 19 Uhr (`hours_v9`, Schutz `max_shorts_day`).
- Mix der 8: **3 Körper/Alltag-Erklärvideos** („Was passiert, wenn du …?“ / „Warum …?“, Du-Perspektive), **2 erzählte Geschichten**
  (`"niche": "Erzählung"`, warm, siehe unten: im Schnitt die stärkste Gruppe mit ca. 1.000 bis 1.700 Aufrufen), **1 Mystery**, **1 Horror**,
  **1 Aktuell-Skript** (siehe unten). Davon **2 in Blockwelt** (`"welt": "block"`, ein Erklärvideo und ein Horror), der Rest Strichmännchen.
- Bei den Zahlen unter „Aktuell“ und „Loop“ unten gilt: Loop-Ende bekommen 3 der 8 (1 Erklärvideo, 1 Mystery, 1 Horror).
- Bis Julius etwas anderes sagt. Nach 5 Tagen prüfen, ob die Aufrufe der ersten 7 Uploads wieder im Schnitt über 600 liegen.

### Aktuell-Skript (seit 23.11.2026, Julius' Wunsch nach dem Video „20 NEW Faceless YouTube Niches“)

Das Video (One Person Business, Verkaufsvideo für eine Community, Einkommenszahlen nicht überprüfbar) nennt als wiederkehrende Muster:
Kanäle explodieren, wenn sie **auf aktuelle Nachrichten aufspringen** (z. B. zum Nvidia-Chef), **Was-wäre-wenn-/Survival-/Geschichts-Erklärer**
mit Animation machen, und **den deutschsprachigen Markt** bedienen (weniger Konkurrenz). Nicht kopieren, nur Muster nehmen. Darum:

- 1 von 8 Skripten pro Tag greift ein **aktuelles Ereignis dieser Woche** auf (Wissenschaft, Natur, Raumfahrt, Technik, Gesundheit, Wetter,
  Rekorde; keine Politik, keine Vorwürfe gegen echte Personen, keine Tragödien mit Toten). Vor dem Schreiben mit der Web-Suche
  **zwei unabhängige Quellen** prüfen, nur belegte Fakten verwenden, keine erfundenen Zahlen.
- Aufbau: Frage in Du-Perspektive zum Ereignis („Was passiert, wenn dein Handy so heiß wird wie bei …?“), Auflösung im vorletzten Satz.
  Im Skript `"aktuell": true` setzen (Lernmerkmal „Aktuelles Thema“ in der Zentrale vergleicht mit „zeitlos“).
- Titel mit dem Ereignis im Kern, aber ohne Clickbait-Lüge. Nach 10 Videos je Seite schauen, ob „aktuell“ klar vorn liegt, dann mehr davon.

Bei 8 Themen am Tag besonders auf Doppelungen achten (nie dasselbe Skript zweimal: am 21.11. lief „Der Schulbus …“ doppelt, das zweite bekam 1 Aufruf) (vorher `seed/` und `docs/videos.json` prüfen).
Lieber ein schwächeres Thema weglassen als eins doppeln oder Fakten erfinden; dann zuerst die 2 Blockwelt-Videos und die Erzählungen schreiben.

Die App hält den Mix selbst (seit 18.11.2026): Seit 23.11. sind von 7 Shorts am Tag 2 Blockwelt (`block_per_day` in der Config, vorher 5 von 15,
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

### Test: Loop-Ende (seit 19.11.2026)

Stand 19.11.: Fast jeder Short bleibt bei ca. 800 bis 1.500 Aufrufen stehen (bester: Schlaf 2.600), egal ob
Erklärvideo, Mystery, Horror, 2D oder 3D. Das Thema ist also nicht die Grenze. YouTube zeigt jeden Short erst
einer kleinen Testgruppe und schiebt ihn nur weiter, wenn die Leute bis zum Ende schauen und nochmal schauen.
Darum als Test: Jeden Tag bekommen **3 der 8 Skripte** (seit 23.11., vorher 5 der 15) `"ende": "loop"`:
1 Erklärvideo (2D), 1 Mystery (2D), 1 Horror (3D).

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
