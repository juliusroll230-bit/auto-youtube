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

Nicht übernommen: `agent-reach` und `reel-analyzer` (laden fremde Videos), alles zu
Instagram-DMs, Leads und Werbung.
