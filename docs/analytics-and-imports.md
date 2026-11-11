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

## Update: Konfliktauswahl, Bestehensquote und direkte Kalendermarkierung

Doppelte Statistikzeilen werden nicht mehr verworfen. In der Importvorschau lässt sich für
jede Kursnummer und jedes Prüfungssemester der gewünschte Eintrag auswählen. Gibt es für einen
geplanten Kurs mehrere historische Semester, wähle die gewünschte Referenz separat aus. Die
Auswahl zeigt Mittelwert, Standardabweichung, Studierendenzahl, Bestehensquote und Quelle.
Alle Alternativen bleiben zusammen mit der Auswahl im verschlüsselten Datensatz erhalten.
Offene Konflikte müssen vor dem Übernehmen aufgelöst werden. Beim Erstellen eines Szenarios
für einen anderen Studienplan können weitere Referenzentscheidungen nötig sein. Die Auswahl
kann dort ebenfalls geändert werden; bestehende Szenarien behalten ihre kopierten Annahmen.

`passRate` enthält die gesamte Bestehensquote der Modulabschlussbewertung in Prozent (0–100,
z. B. `85` für 85 %), unabhängig von Mittelwert/Standardabweichung. Ein fehlender Wert bleibt
`null`; ältere JSON-Dateien ohne dieses Feld bleiben gültig. Die PDF-Prompts verlangen die
Bezugsgruppe und unterscheiden Gesamtquote von Teilprüfungsquoten. Eine Berechnung ist nur
aus dokumentierten bestandenen/insgesamt bewerteten Ergebnissen erlaubt.

Im Stundenplan direkt in der Kalenderfläche klicken und ziehen. Der Bereich wird in
Viertelstunden markiert; nach dem Loslassen erscheint ein Menü mit den Modulen des Zielsemesters,
Beginn/Ende und Raumfeldern. Modul auswählen und speichern. Weitere Markierungen desselben Moduls
fügen zusätzliche Termine hinzu. Escape/Abbrechen verwirft die Markierung. Gesperrte Module sind
nicht auswählbar. Eine Zeitzelle lässt sich auch mit Enter/Leertaste öffnen und per Formular anpassen.
Die bisherige manuelle Eingabe und Modul-Drag-and-drop bleiben verfügbar.

## Update: conflict choices, pass rate and time-first calendar

Duplicate statistic rows now offer explicit source choices in the import preview. When several
historical terms match a planned module, choose the reference for that target semester. Alternatives
and selections remain together in the encrypted dataset. Resolve conflicts before applying an import;
a different scenario plan can require additional term choices. Changing a dataset choice affects
future scenario creation; existing scenarios retain their copied assumptions.

The optional `passRate` is the overall final module pass percentage on a 0–100 scale, e.g. `85`
means 85%. Unknown is `null`; old JSON remains valid. Both PDF prompts request the denominator and
forbid inferring a pass rate from the mean/deviation or substituting component pass rates.

Click and drag directly across a calendar day to select a time range, then choose a module in the
picker and save. Selection snaps to 15 minutes, supports reverse dragging and can be edited in the
form. Repeating the flow adds more weekly meetings. Escape/Cancel discards the selection. Only
unlocked modules assigned to the current plan/semester can receive meetings. Keyboard activation
of a time cell opens the same picker. The older manual and module-first flows remain available.

## Update: Ersatznoten, lokale Überschreibungen und Szenarien speichern

In **Studiensimulation** kann eine **globale Ersatznote** von 1 bis 6 für Module ohne verwendbare
importierte Note gesetzt werden. Ein leeres Feld bedeutet unbekannt, niemals Note 0. Die Ersatznote
kann bereits beim Erstellen oder später beim ausgewählten Szenario eingestellt werden.

Die kompakte Modultabelle zeigt Note, Semester, Kategorie und Quelle. Eine **lokale Modulnote**
eintragen und übernehmen, um ein einzelnes Modul zu überschreiben. **Standard verwenden** entfernt
die lokale Annahme und verwendet wieder Statistik oder Ersatznote. Suche und Quellenfilter helfen,
fehlende Annahmen und Überschreibungen zu finden. Statistikquellen sind aufklappbar; Teilnoten und
eigene Formeln bleiben über die Details verfügbar. Das bloße Öffnen der Details oder Ändern einer
Zielnote friert einen Statistikwert nicht als lokale Annahme ein.

Vorrang: echte Ergebnisse (wenn im Szenario übernommen), lokale Annahmen, verwendbare importierte
Noten, globale Ersatznote, unbekannt. Bei echten Teilnoten dient eine lokale/globale Modulnote als
Ziel für die offenen Leistungen; bekannte Teilnoten, Bonus und Bewertungsformel bleiben geschützt.
Ein unerreichbares Ziel wird markiert. Die regulären Regeln zur Master-Gesamtnote gelten weiterhin.

**σ ändern** betrifft nur ausgewählte Statistikmodule. Lokale Überschreibungen, Module ohne Import
und manuell ergänzte Noten bei lückenhaften Statistiken werden nicht zurückgesetzt. Ist die neue
σ-Annahme nicht berechenbar, bleibt eine vorhandene Annahme bestehen. Fehlt schon bei der Erstellung
eine verwendbare Statistiknote, gilt die Ersatznote oder unbekannt. Die σ-Auswahl zeigt geschützte
Module an; je Modul bleibt der tatsächlich angewendete Faktor nachvollziehbar.

**Szenarien speichern** sichert alle benannten Szenarien samt Ersatznoten, Überschreibungen,
Statistikdaten und zuletzt gewähltem Szenario in `grades.enc`. Die Leiste zeigt ungespeicherte
Änderungen, Speichervorgang und gespeicherten Stand. Gültige noch offene Inline-, Ersatznoten- und
σ-Eingaben sowie bearbeitete Simulations-Teilnoten werden beim Speichern übernommen. Ungültige
Eingaben blockieren den Speichervorgang mit einer Meldung. Nach dem Neuladen den Notenspeicher mit
dem bisherigen Passwort öffnen; die Szenarien und die gespeicherte Auswahl sind wieder da.

## Update: fallback grades, local overrides and saving scenarios

Set a **global fallback grade** (1–6) for courses without a usable imported grade, either during
scenario creation or later. Blank means unknown, never grade zero. The compact course table shows
where each grade comes from. Apply a local module grade to override one course; **Use default**
returns it to imported statistics or the global fallback. Search and source filters help locate
missing assumptions and overrides. Expand statistics for provenance, or open details for components
and custom formulas. Viewing details or changing a target grade alone does not create an override.

Actual results take priority when inherited, followed by local overrides, usable imported grades,
the global fallback and unknown. For partially graded modules, an assumed module target is solved
against the remaining components while preserving actual grades, bonus and formula. Unreachable
targets remain marked. The normal final-degree grade/category checks still apply.

Changing **sigma** updates selected statistical courses while preserving local grades and unmatched
courses. Imported rows missing a mean/deviation no longer erase manual assumptions. If a new sigma
assumption cannot be calculated, the existing assumption remains. A course starting without a usable
statistical grade uses the fallback or stays unknown. Per-course metadata shows the applied factor.

**Save scenarios** persists all named scenarios, fallbacks, overrides, statistics and the selected
scenario in the encrypted vault. The toolbar shows unsaved, saving and saved states. It includes
valid pending inline/default/sigma edits and modified simulation components; invalid edits show an
error instead of being silently saved. Reload, unlock with the same password, and the saved scenarios
and selection are restored. Scenario data is never added to the public study-plan JSON.
