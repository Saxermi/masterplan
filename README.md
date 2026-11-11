# MasterPlan

A local-first, bilingual study planner for the ETH Zurich MSc Computational Science and Engineering programme. **Academic Minimal** UI, no Node.js, Docker or frontend build needed.

> **Status: usable early MVP, not a finished official degree audit.** Course searches use the independent [VVZAPI](https://github.com/markbeep/vvzapi); study requirements are provisional starter thresholds. No ETH affiliation or warranty. Always verify credit eligibility, registration, examination schedules and the binding personal regulations with ETH.

## Start / Starten

**Ubuntu/Linux and macOS** (Python 3.10+):

```sh
sh run.sh
```

**Windows** (Python 3.10+): double-click `run.bat`. It opens `http://127.0.0.2:8765/`. A browser-only hosted edition and standalone installers are **not yet provided**. Use `python3 server.py --no-browser --port 8765` for headless operation.

The default bind address is **`127.0.0.2:8765`** (as requested). If this loopback alias is unavailable on Windows/macOS, MasterPlan automatically falls back to `127.0.0.1:8765` and prints the actual URL. Override with `sh run.sh --host 127.0.0.1` when needed. Only loopback connections are supported.

**German:** `sh run.sh` starten und `http://127.0.0.2:8765/` öffnen. Keine Kommandozeile ist für die Nutzung der Weboberfläche erforderlich, wenn die App schon läuft. Für den ersten lokalen Start wird Python benötigt. Windows: `run.bat` doppelklicken.

## Implemented / Umgesetzt

- Bilingual **Deutsch / English**, Academic Minimal light/dark interface and responsive PWA manifest.
- Named study scenarios: create, duplicate, switch, rename, delete, compare, per-plan semester columns.
- Local course records, manual events with building/floor/room, time clash detection and shared completed-course history.
- Course/semester locks, interest-only courses (always **0 credited ECTS**), preliminary credit categories.
- **Offline-first VVZ dump**: one complete SQLite database snapshot (ZIP) is downloaded on first start, stored under a gitignored cache directory, and reused across restarts for course search, details, exercise groups and timetable slots. Same-season historical proxies and all existing programme/category filters remain available. Upstream calls are globally limited to **one request per minute**.
- Separate grade page with a password-encrypted `grades.enc` (AES-GCM via browser WebCrypto; PBKDF2 250,000 iterations), component-weighted estimates. Grades appear only in the protected Grades and Study simulation views.
- Minimal local JSON, atomic revisions, independent encrypted grade storage, JSON plan export/import, portable data folder (can be inside a cloud-sync folder). Open/move folders through Settings.
- Configurable guideline JSON + schema for a future external extraction agent. Includes starter study-progress indicators, not full curriculum adjudication.

## Not yet implemented / Noch offen

- Validated autonomous PDF-guidelines extraction/approval pipeline, full legal applicability and admission checks, exact seminar validation and final official graduation grade.
- Complete event reconciliation and automatic updates of previously chosen personal slots remain conservative: VVZ schedule changes are flagged, but never silently overwrite selected or manual slots. Some by-appointment or date-specific events have no weekly slot and must be handled manually.
- Cloud merge/conflict resolution between two simultaneous editing devices. **Do not edit the same cloud-synced folder from two computers at once**; sync fully before switching.
- Cloud-hosted deployment, automatic desktop installers, production accounts and hosted multi-user security. This server is **local loopback only**.
- Scheduled live-upstream contract tests, a broad browser/OS matrix, accessibility auditing and continuous release/distribution. Allocation, storage, HTTP and synthetic browser regressions run in CI.


## Feedback revision (November 2026) / Überarbeitung

- **Real study progress vs scenarios** / **Tatsächlicher Verlauf vs Szenarien**: dashboard and top semester board now show actual progress, while named hypothetical specialisation scenarios are separate below; the former is never overwritten when switching scenario.
- **Shortlist first** / **Erst Merkliste**: catalogue results can be shortlisted, then assigned from a dropdown in Semester planning. Assigned courses can be unselected without deleting their shortlist entry. The timetable add-event form selects only courses already assigned to its semester.
- **Study programme/category/term filters**: MSc CSE is default, and its official section path is distinct from the RW/CSE Bachelor; category filters support Core Courses, Electives, specialisations, case studies, semester projects, Science in Perspective, master thesis and Scientific Works (zero credits). Separate RW Bachelor admission requirements are tracked **outside** MSc ECTS. The default recent-term window is previous two / current / next. Historical same-season proxies are labeled.
- **Specialisation filters**: selected specialisations narrow VVZ section-path search; empty selection yields no specialisation results. Eligible ETH MSc core-course programmes can be searched as potentially creditable CSE electives, subject to individual recognition.
- **Required Study Achievements** on actual dashboard and per scenario: 120 total; 74 main-area credits; two core courses ≥12 ECTS; four specialisation lectures and one seminar ≥18 ECTS; two electives ≥12 ECTS; two case studies (3 ECTS each); term project 8; SiP 2; thesis 30; Scientific Works prerequisite at Bachelor/Master level, and separately selected admission conditions. Core Courses **Advanced Machine Learning** and **Probabilistic Artificial Intelligence** may not both count as cores. Figures are provisional because individual regulations and actual credit approval must be checked.
- **Graduation grade formula** from MSc-CSE Guidelines §3.3 (p. 10): `(2*core1 + 2*core2 + SUM(four specialisation lecture grades) + SUM(all included elective grades) + 4*thesis_grade) / (12 + number_of_included_electives)`. Each module's internal component grades may first be averaged by its own assessment weights. Grade values never appear outside the private grade page.
- **Actual VVZ timetable** / **Termine aus VVZAPI**: `/api/v1/course/get/{id}` gives real weekday/start/end/building/floor/room, and `/api/v1/unit/{id}/get` includes exercise groups. They are read locally from the installed VVZ dump (or fetched through the shared one-per-minute API fallback while the dump is missing), with selectable timeslots and room data; API source/link, historic proxy flag, and optional CourseReview link appear on linked modules. No synthetic times are inserted into personal data.
- **Course links** / **Verlinkungen**: direct official ETH VVZ for an identified learning unit, or official VVZ number search as fallback; CourseReview links appear only if VVZAPI reports a CourseReview rating. CourseReview is not affiliated with ETH.

Run the optional browser UI regression test with `python3 tests/browser_smoke.py` (developer dependency Playwright/Chromium only). It uses mocked local responses and synthetic course data; no personal data or live API traffic.

### Limitations / Grenzen

The full Guidelines extraction agent is still a future component; a manually reviewed machine-readable rule starter is used, not a binding graduation audit. Programmatic identification of the exact *anrechenbar* course category from the student's admission ruling requires manual confirmation. VVZ timeslots missing times or listed only "by appointment" cannot be rendered as weekly recurring events. Auto-scheduling exercise groups is deliberately opt-in because group selection is personal. A public hosted edition/desktop installer is still not delivered.

## Storage / Datenspeicher

Default: `./user-data/masterplan.json` and (only if grades are saved) `./user-data/grades.enc`. Use environment variable `MASTERPLAN_DATA_DIR` before starting, or Settings → Move/Open data folder (path can be a Nextcloud/OneDrive/iCloud/Dropbox local sync folder). JSON stores personal selections rather than huge VVZ catalogues. Personal data paths are in `.gitignore`. Export and import covers study plans, **not** the grade vault. Back up both files together; loss of the grade password makes the grade vault unrecoverable. The web app is local HTTP, not automatically authenticated to any cloud service.

## VVZ data integration / Offline-Dump

**New workflow / Neue Funktionsweise:**

1. On the first start, the local server fetches the small `GET https://vvzapi.ch/api/v1/dump/metadata` JSON (size and `last_modified_ms`). Only if no valid database is installed, or if the metadata changed, it downloads `GET https://vvzapi.ch/api/v1/dump` as a ZIP. Downloaded bytes are streamed to disk instead of held in memory.
2. The ZIP is checked for expected size, SQLite format, required schema and `PRAGMA quick_check`. Only after a successful validation does an atomic replacement make the new snapshot active. A corrupt or failed download leaves the previously working snapshot usable.
3. Course catalogue searches, MSc CSE / RW Bachelor / other programme filters, category/section filters, semester and historical-proxy choices, learning-unit details and real lecture/exercise-group timeslots are then queried **locally** using SQLite. No VVZ HTTP requests are needed for catalogue search. Missing weekly schedule data is loaded from the official ETH VVZ only on demand and persisted locally.
4. The app checks **only metadata** at most once every **24 hours** (and on explicit user request in Settings → Offline VVZ catalogue). If size *and* last modification timestamp are unchanged, the ZIP is **not downloaded again**. Metadata is persisted, so this also survives server restarts. Offline searches remain available while a new snapshot is being downloaded.
5. A single server-wide limiter covers metadata, ZIP downloads and the temporary online fallback: **maximum one request per minute**, implemented as one reservation every 60 seconds. The VVZ dump endpoint itself permits up to 2/minute; MasterPlan deliberately stays below that limit. The initial download may therefore start 60 seconds after its metadata request. If the dump is unavailable, catalogue search reports installation status; existing personal plans remain accessible.

**Persistence / Speicherort:** Default `.cache/vvz/database.sqlite` and `.cache/vvz/metadata.json` in the app directory; override with `MASTERPLAN_CACHE_DIR=/your/cache/folder`. This cache is disposable and **is never copied into `MASTERPLAN_DATA_DIR`** (your personal portable/cloud-sync folder). It is covered by `.gitignore`, along with temporary ZIPs and local SQLite files. All actual study plans and encrypted grades are stored separately.

**Endpoints / API:** `GET /api/vvz/dump/status` displays database availability, phase, size and last check; `POST /api/vvz/dump/check` forces a background metadata check. The original `/api/vvz/search`, `/api/vvz/unit/{id}` and `/api/vvz/times/{id}` keep their response formats and prefer the local database.

**Source:** VVZAPI is an independent, community-maintained project at [markbeep/vvzapi](https://github.com/markbeep/vvzapi). Its ZIP endpoint is rate-limited; metadata is the documented way to avoid needless downloads. The local dump is not an authoritative statement of individual course eligibility. Always confirm planned lectures and recognition using the official ETH VVZ and your current regulations.

**Offline note:** The installation needs network access for the initial dump. While the first download runs, catalogue search reports that the local snapshot is being prepared. A cached snapshot works offline. The dump's freshness is checked only while the local server is running or the user explicitly asks. The downloadable archive can be large, depending on the upstream data. The application has no automatic cloud-sync conflict resolution.

## Guidelines agent contract

An external agent should produce `guidelines/cse-guidelines.json` conforming to `guidelines/cse-guidelines.schema.json`. Each confidently extracted rule should include provenance (page and document source), regulation applicability and extracted text. The checked starter file has `sourceChecked: false`, and unknown data must not be invented. The app reads the configured thresholds but **does not automatically grant official academic recognition**. Do not commit private documents or personal records.

## Allocation audit and feature inventory

See the [implemented features and remaining gaps](docs/feature-inventory.md) and
[allocation validation report](docs/allocation-validation.md). The audit checks course counts,
category credits, duplicate/Bachelor/admission credit reuse, seminar composition and grade selection.
**More than 130 ECTS is allowed and triggers only a transcript-selection warning.** Extra electives
cannot replace missing required categories. Incomplete drafts remain saveable.

The manual course editor supports specialisation lecture/seminar and Bachelor-credit-use fields.
The checks are provisional; personal recognition and full major/minor applicability still require review.

## Development / Entwicklung

Python standard library only. Run Python tests with `python3 -m unittest discover -s tests -v` and allocation/grade tests with `node --test tests/study-rules.test.cjs` (Node 22+ is a developer-test dependency only). Browser regression commands are listed in the allocation validation report. To adjust listening port, use `sh run.sh --port 9000`. To stay on loopback, do not change the bind address to `0.0.0.0` unless you add authentication and proper security controls. The built-in HTTP server is **not suitable for untrusted public hosting**.

Project tree:

```
server.py                 local server, file persistence, VVZAPI proxy
web/                      semantic HTML, responsive CSS, browser JavaScript
guidelines/               machine-readable rule contract + starter rules
tests/                    server logic and storage tests
run.sh / run.bat          single-command/double-click startup
user-data/                private local data, gitignored (created on first run)
```

## Design values

Low data footprint, no grade leakage, no silent overwriting of locked semesters, clear differentiation of **planned** and **completed**, explicit historic proxies and visible uncertain academic recognition.

## Screenshots / Bildschirmfotos

Browser-rendered captures of the real Academic Minimal frontend using **synthetic demo data**, not real student records. They are intentionally kept separate from `user-data/`.

| Dashboard | Semester planning |
| --- | --- |
| ![Dashboard with ECTS summary](docs/screenshots/01-dashboard.jpg) | ![Semester planning with locked terms and historical proxy](docs/screenshots/02-semesters.jpg) |

| Plan comparison | ETH module catalogue |
| --- | --- |
| ![Saved study plans and comparison](docs/screenshots/03-plans.jpg) | ![Course catalogue with degree filters](docs/screenshots/04-catalog.jpg) |

To regenerate: `python tests/create_screenshots.py` (optional developer dependency `playwright` plus Chromium, not required for normal users). Screenshots are taken from actual frontend HTML/CSS/JavaScript with a mocked backend; no production data, grades, or ETH API results are involved.

| Automatic VVZ timetable and optional CourseReview links |
| --- |
| ![Timetable with VVZ API slots and links](docs/screenshots/07-api-timetable.jpg) |


### CSE elective core-course filter / CSE-Elective-Core-Filter

The catalogue includes **“MSc Core Courses → CSE Electives”** with a one-click option to browse all eligible Master's programmes or narrow to one programme. The eligible study programmes are Statistics, Physics, Computer Science, Mathematics (including Applied Mathematics), Neural Systems and Computation, Robotics, Systems and Control, Data Science, and Electrical Engineering and Information Technology. This list follows the [MSc CSE Guidelines, section 3.6, p. 19](https://ethz.ch/content/dam/ethz/special-interest/study-programme-websites/ms-compsci-and-eng-dam/documents/master-programme/MSc-CSE-Guidelines.pdf). It uses VVZAPI section-path filters, with **Core Courses**, not general elective labels.

A filtered course is **potentially eligible without prior approval**, not guaranteed to be credited: exclusions such as previous Bachelor credit use, category duplication, personal study regulations, and current VVZ classifications still apply. The study planner does not submit ETH credit requests. / Ein Treffer bedeutet **grundsätzlich ohne vorgängige Bewilligung wählbar**, nicht automatisch angerechnet. Vorherige Bachelor-Anrechnung, Doppelzählungen, persönliche Reglementsfassung und aktuelle VVZ-Einstufung müssen geprüft werden.

The **Study plans → Semester vs. semester** view allows comparing any two semesters from the same or different plans side by side, including common/unique modules, category/ECTS/status differences, locked and extra courses. This UI-only selection does not increase the saved study-plan file size. / Unter **Studienpläne → Semester vs. Semester** können zwei beliebige Semester aus gleichen oder unterschiedlichen Plänen modulweise verglichen werden.

### HS26 catalogue and save repairs / Katalog- und Speicherreparaturen

See [verified HS26 example, timings and test commands](docs/hs26-validation.md) and the
[importable AI Core + Numerical Methods admission-requirement plan](docs/examples/hs26-ai-numerical.json).
Existing dumps are indexed automatically without downloading them again. Search metadata is tied to
the selected offering, with exact programme/specialisation scopes and paginated results. Browser
saves are serialized; external revision conflicts are reported without overwriting the newer version.

The current upstream dump omits most lecture times. Missing weekly schedules are fetched lazily
from the official ETH VVZ, queued behind the shared one-request-per-minute gate, and persisted
outside the personal data folder. Cached schedules survive restarts and refresh in the background
after 24 hours. Irregular/date-specific times still require manual review. Initial catalogue search
waits for the validated local dump; it does not issue broad compact-API searches during installation.

### Offline VVZ catalogue / Lokaler VVZ-Katalog

![Offline catalogue status and update check (synthetic demo)](docs/screenshots/08-offline-catalog.jpg)

The screenshot uses mocked, non-personal data. The UI reports whether the local SQLite dump is available and allows an explicit metadata check without downloading an unchanged archive.

### Semester and allocation workflow update

The catalogue defaults to a concrete semester. Its recent choices span the previous two, current
and next two semesters; an optional second concrete semester allows browsing autumn and spring
together. Catalogue results and allocations prefer confirmed offerings and otherwise allow labelled historical references. Source unit IDs and source semesters are retained. Manual modules remain freely schedulable.

Semester columns include removal with lock checks and confirmation for populated semesters;
shortlist entries and completed history are retained. The timetable includes an inline assignment
form and a manual-time form with a direct VVZ link for the selected module. Course cards provide
“Change allocation” to adjust the target plan, semester and credit category. Changing semester clears
selected events; locks and duplicates are checked. Historical and cross-season references are allowed with separate warnings. Empty scenarios now open correctly.

Science in Perspective uses the shared catalogue section; Scientific Works in Mathematics/Physics
are found by their official module numbers. Eligible MSc core electives display the matching Master
programmes. Run `python3 tests/browser_semester_flow.py` for the synthetic regression workflow.

### Batch allocation and moving courses

The assignment form provides a searchable checkbox shortlist with multi-selection, select-visible
and clear-selection actions. Modules already allocated or completed in the chosen target plan are
hidden. Alternative scenarios retain independent choices. A batch is validated and saved together;
its modules can keep their individual suggested credit categories.

Unlocked semester cards can be dragged to another semester or plan. Course/semester locks,
duplicate allocations and confirmed offerings are checked again when saving. Selected times reset
when the semester changes. The existing “Change allocation” editor remains available for keyboard
and touch workflows. Developer regression: `node --test tests/*.test.cjs` and
`python3 tests/browser_bulk.py` (native Chromium drag-and-drop, synthetic data only).

### Spezialisierungsseminar / Specialisation seminar

Die Anrechnungskategorie **Spezialisierungsseminar** ist direkt bei Zuweisung, Mehrfachauswahl,
manueller Erfassung und nachträglicher Zuordnungsänderung verfügbar. Im englischen Interface heißt
sie **Specialisation seminar**. Intern bleibt sie Teil der Spezialisierung: ECTS zählen dort, das
Seminar zählt einmal und ersetzt keine der vier Vorlesungen. Seminar-Noten bleiben aus der
Schlussnotenformel ausgeschlossen. Bestehende Einträge mit `role=specialisation, subtype=seminar`
bleiben kompatibel. Fehlt die Art, wird das Wort „Seminar“ im Titel als Hinweis verwendet; eine
explizite Eintragung als Vorlesung hat Vorrang.

The category **Specialisation seminar** is available in assignment, batch selection, manual entry
and the allocation editor. It remains part of specialisation credits while counting separately from
its four lectures. Seminar grades are excluded from the final-grade formula. Existing seminar
records remain compatible. Missing subtype metadata can use “Seminar” in the title as a hint;
an explicit lecture classification takes precedence. Academic field recognition remains provisional.

### Kursdetails, historische Angebote und Zeitzellen / Course details, references and time cells

Modultitel sind anklickbar. Beschreibung, Lernziele, Inhalte und Literatur kommen aus dem lokalen
VVZ-Dump bzw. dem vorhandenen Unit-Endpunkt. Die Ansicht nutzt die gewählte Sprache und fällt
bei fehlender Übersetzung auf den vorhandenen Text zurück. Fehlende Daten sind explizit markiert;
Kurstexte werden als Text dargestellt, nicht als ausführbares HTML. Die Abfrage erfolgt erst beim
Öffnen und wird pro Unit-ID im Browser zwischengespeichert; die persönliche Plandatei bleibt klein.

Historical course references may be assigned, moved and saved. The actual source unit/semester
is preserved. Missing exact-term offerings show a historical-reference warning; a spring/autumn
mismatch shows a second warning. Known same-season history is preferred. These warnings do not
invalidate a degree plan, and existing course/semester locks still apply.

Im Stundenplan werden die zugewiesenen Module des Zielsemesters angezeigt. Modul auswählen und
eine Zeitzelle anklicken oder das Modul in eine Zeitzelle ziehen: Das Formular wird vorausgefüllt.
Beginn/Ende prüfen und speichern; weitere Termine desselben Moduls werden hinzugefügt, nicht ersetzt.
The target-semester module palette and time-cell click/drop flow support multiple meetings per
module. Existing selected meetings reset when changing the course allocation's semester.

Regression: `python3 tests/browser_history_details.py` uses synthetic public-shaped metadata and
an isolated temporary data folder; it does not modify personal plans.

### Studiensimulation / Study simulation

Der eigene Menüpunkt **Studiensimulation** enthält benannte, duplizierbare und löschbare
Notenszenarien. Jedem Szenario wird ein Studienplan zugeordnet; dessen Module und Kategorien
bestimmen die simulierte Schlussnote. Beim tatsächlichen Verlauf werden echte Ergebnisse über
Kursverknüpfung, Kursnummer oder einen eindeutigen exakten Titel übernommen. Bekannte Noten und
Bewertungsgewichtungen sind in der Simulation geschützt; Annahmen füllen nur offene Leistungen.

Both **Grades** and **Study simulation** use form-based component editing: assessment names,
weights, actual grades, separate assumptions for pending work, a target module grade, and an additive
bonus such as +0.25. Forecasts show the known-component average, a possible 1–6 range, the required
average on pending assessments and the grade resulting from entered assumptions. Bonuses are added
after the weighted average and grades are capped at 6. Actual final grades do not use assumptions.

**Änderungen mit „Übernehmen“ bestätigen und anschließend „Verschlüsselt speichern“.** Noten und
Simulationen werden zusammen in `grades.enc` gespeichert; sie erscheinen weder in der normalen
Plandatei noch im Planexport. Beim Verlassen beider privaten Ansichten wird der Speicher gesperrt.
Vorhandene verschlüsselte Notendateien bleiben kompatibel. Für alte manuelle Noteneinträge mit
abweichendem Titel kann im Noteneditor eine explizite Kursverknüpfung gewählt werden.

**Apply edits, then choose Save encrypted.** Real marks and scenarios share the password-encrypted
vault; actual marks remain separate from hypothetical assumptions. Leaving both private views locks
the vault. Simulated averages use the same category weights and exclusions as the grade page;
recognition and individual assessment regulations remain subject to manual verification. Developer
coverage: `node --test tests/*.test.cjs` and `python3 tests/browser_grades.py`.


Die Modulbearbeitung verwendet jetzt ebenfalls ein Formular mit Dropdowns für Semester,
Anrechnungskategorie und Status statt Browser-Eingabefenstern. Titel, ECTS, Spezialisierungsgebiet
und Bachelor-Verwendung können dort gemeinsam bearbeitet werden. Die Quellen-/Sperrprüfungen
bleiben bestehen. / Course editing now uses a form with semester, category and status dropdowns
instead of native browser prompts. Pending manual timetable input survives background schedule refreshes.

### Flexible Formeln, JSON-Statistiken und Modulnotizen / Formulas, statistics and notes

Noten und Simulationen unterstützen eigene `min`/`max`-Formeln mit mehreren Zwischenprüfungen,
Bonusplatzierung und einstellbarer Maximalnote. JSON-Statistiken mit Mittelwert, Standardabweichung,
Studierendenzahl und Quelle erzeugen anpassbare Szenarien. Echte Noten werden nur nach ausdrücklicher
Auswahl übernommen. Moduldetails enthalten persönliche Notizen und importierbare
Vorbereitungseinschätzungen. Studienpläne lassen sich semesterübergreifend mit VVZ-Links exportieren.

Custom formulas, JSON statistics/sigma scenarios, course notes and preparation assessments are
available in both languages. See the [workflow and JSON examples](docs/analytics-and-imports.md),
[PDF extraction prompts DE/EN](docs/prompts-statistics.md) and
[preparation prompts DE/EN](docs/prompts-preparation.md). The timetable now shows event duration,
quarter-hour starts and overlapping meetings accurately. `python tests/browser_analytics.py`
checks these flows with synthetic data.
