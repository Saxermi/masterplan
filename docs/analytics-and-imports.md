# Noten, Statistikimporte und Vorbereitung / Grades, statistics and preparation

## Deutsch

- **Noten → Bearbeiten:** beliebig viele Teilnoten mit eigenen Variablennamen. Leer bedeutet
  unbekannt; eine Annahme bleibt von einer echten Note getrennt. Ohne eigene Formel gelten die
  relativen Gewichte. Mit eigener Formel bestimmen deren Koeffizienten die Gewichtung; die
  Prozentspalte wird dann ignoriert.
- Beispiele: `max(F, 0.8*F + 0.2*M)` oder
  `max(F, 0.8*F + 0.2*M1, 0.6*F + 0.2*M1 + 0.2*M2)`. Erlaubt sind
  Zahlen mit Dezimalpunkt, Variablen, `+ - * /`, Klammern, `min()` und `max()`.
  Die Vorlagen erhalten vorhandene F-/M-Noten. Individuelle Gewichte und Notengrenzen lassen sich
  mit der Formel und der maximalen Modulnote abbilden; Rundungsfunktionen fehlen.
- Ein Bonus wie `0.25` wird nach der Formel addiert oder ausdrücklich über `B` in der Formel
  verwendet. Das Ergebnis bleibt zwischen 1 und der eingestellten maximalen Modulnote (höchstens 6).
  Das angezeigte Intervall ist konservativ; die numerische Zielnotensuche setzt bei mehreren
  offenen Leistungen denselben angenommenen Wert an und ersetzt keine individuelle Prüfungsregel.
- **Studiensimulation → Statistik / Notenszenario als JSON importieren:** JSON-Datei laden oder
  Text einfügen, Vorschau prüfen und übernehmen. Mittelwert, Standardabweichung, Anzahl
  bewerteter Studierender, Prüfungssemester und Quelle bleiben erhalten. Es gibt keinen PDF-Import
  in der App: [diese Prompts](prompts-statistics.md) zusammen mit dem PDF in ChatGPT verwenden,
  das ausgegebene JSON prüfen und anschließend hier importieren.
- Ein Statistikdatensatz kann mehrere Szenarien erzeugen: `−1` bedeutet Mittelwert minus eine
  Standardabweichung, `0` Mittelwert, `+1` Mittelwert plus eine Standardabweichung. Der Faktor
  kann später für ausgewählte oder alle Module angepasst werden. Ergebnisse werden auf 1–6
  begrenzt. Fehlender Mittelwert oder eine benötigte fehlende Standardabweichung bleiben unbekannt.
  Mehrdeutige Kurszuordnungen werden nicht geraten; ein exaktes Semester hat Vorrang.
- Bei jeder Szenarioerstellung ausdrücklich **Ja/Nein** zur Übernahme echter Ergebnisse wählen.
  Übernommene echte Teilnoten und ihre Bewertungsformel sind geschützt. Statistikannahmen füllen
  offene Leistungen, soweit mit den echten Ergebnissen erreichbar. Eine vollständige Master-Gesamtnote
  erscheint erst, wenn die benötigten anrechenbaren Noten vorliegen und die Kategorien stimmen.
- Änderungen zuerst **Übernehmen**, dann **Verschlüsselt speichern**. Noten, Statistiken und
  Szenarien liegen zusammen im privaten Notenspeicher `grades.enc`; Planexporte enthalten sie nicht.
- **Modultitel anklicken:** Kursinformationen, persönliche Notizen und importierte Einschätzungen
  sind getrennte Bereiche. Notizen und Vorbereitungseinschätzungen liegen im normalen
  Studienplan-JSON, also unverschlüsselt. Sie gelten nicht als echte Noten oder offizielle Anerkennung.
- **Studienpläne → Export:** JSON/CSV enthält alle zugewiesenen Semester mit Kategorie, ECTS,
  Status, VVZ-Link und historischem Quellsemester. Der Vorbereitungsexport ergänzt verfügbare
  Kursbeschreibungen/Lernziele. Persönliche Notizen nur nach Aktivieren der Checkbox.
  [DE/EN-Prompts](prompts-preparation.md) helfen ChatGPT, daraus eine chronologische Einschätzung
  zu erzeugen. Importvorschau prüfen; Einschätzungen erscheinen beim Modul im bewerteten Semester.
- **Stundenplan:** Zielsemester wählen, Modul in Zeitzelle ziehen oder Modul und Zeitzelle
  anklicken. Beginn/Ende und Raum prüfen, speichern; für weitere Wochentermine wiederholen.
  Beispiel Dienstag 16:00–18:00, HG F 5. Viertelstunden, Dauer und Überschneidungen werden dargestellt.

Beispieldateien: [Prüfungsstatistik](examples/exam-statistics.json),
[Notenszenario](examples/grade-scenario.json), [Vorbereitung](examples/preparation.json).
Alle Beispiele und Screenshots verwenden erfundene Daten.

## English

Use **Grades → Edit** for arbitrary assessment components, actual marks and separate assumptions.
Leave unknown results empty. A blank formula uses relative component weights; a custom arithmetic
formula overrides the percentage column. The two max-rule templates above preserve existing final
exam and midterm results. Add a bonus after evaluation or place `B` explicitly inside the formula;
choose a module grade ceiling up to 6. The remaining-grade solver is numerical and uses a common
assumed value for multiple pending assessments; interval bounds are conservative.

Use **Study simulation → Import statistics / grade scenario JSON** to preview and apply validated
JSON. The app imports JSON only. Give the bilingual [statistics prompts](prompts-statistics.md)
and your PDF to ChatGPT, verify the extracted data, then import its JSON. Keep unknown statistics
as `null`. Dataset provenance is retained. Create scenarios at mean ± a chosen deviation factor,
and adjust selected courses later. Missing required deviations remain unknown, rather than invented.
Exact-term matching wins; ambiguous matches are skipped. Every creation/import of a grade scenario
requires an explicit choice about inheriting actual grades. Inherited results and rules are protected.

Apply edits, then **Save encrypted**. Marks, statistics and scenarios live only in the encrypted
vault. The same degree-grade weights and category checks apply to real and simulated final grades.

Click a course title for supplied description/objectives, personal notes and separate preparation
assessments. Notes and advisory assessments are stored unencrypted with study plans. Under
**Study plans**, export all assigned semesters to JSON/CSV with official VVZ/source-term links.
The preparation context also includes available course information and optionally your notes.
Use the [preparation prompts](prompts-preparation.md), then preview/import the returned assessment
JSON. Assessments do not alter allocations or official recognition.

The timetable supports repeated meetings for one course, minute-accurate positioning, event duration
and overlap lanes. Choose the target semester and module, click/drop onto a time cell, review the
prefilled form and save each meeting. Calendar recurrence exceptions and automatic group optimisation
remain outside this change.

## Reproduce review screenshots

```sh
SCREENSHOT_DIR=docs/screenshots python tests/browser_analytics.py
```

This launches Chromium against an isolated temporary HTTP server and synthetic catalogue/plan.
It exercises imports, encrypted roundtrip, exports, formulas, persisted notes/assessments and calendar
geometry. It never reads personal grade or plan files.
