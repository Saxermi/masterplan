# MasterPlan

A local-first, bilingual study planner for the ETH Zurich MSc Computational Science and Engineering programme. **Academic Minimal** UI, no Node.js, Docker or frontend build needed.

> **Status: usable early MVP, not a finished official degree audit.** Course searches use the independent [VVZAPI](https://github.com/markbeep/vvzapi); study requirements are provisional starter thresholds. No ETH affiliation or warranty. Always verify credit eligibility, registration, examination schedules and the binding personal regulations with ETH.

## Start / Starten

**Ubuntu/Linux and macOS** (Python 3.10+):

```sh
sh run.sh
```

**Windows** (Python 3.10+): double-click `run.bat`. It opens `http://127.0.0.1:8765/`. A browser-only hosted edition and standalone installers are **not yet provided**. Use `python3 server.py --no-browser --port 8765` for headless operation.

**German:** `sh run.sh` starten und `http://127.0.0.1:8765/` öffnen. Keine Kommandozeile ist für die Nutzung der Weboberfläche erforderlich, wenn die App schon läuft. Für den ersten lokalen Start wird Python benötigt. Windows: `run.bat` doppelklicken.

## Implemented / Umgesetzt

- Bilingual **Deutsch / English**, Academic Minimal light/dark interface and responsive PWA manifest.
- Named study scenarios: create, duplicate, switch, rename, delete, compare, per-plan semester columns.
- Local course records, manual events with building/floor/room, time clash detection and shared completed-course history.
- Course/semester locks, interest-only courses (always **0 credited ECTS**), preliminary credit categories.
- VVZAPI compact course search by CSE or selected other ETH degree; semester-matching and same-season historical proxies, persistent course-number references; globally throttled upstream to at most one request per minute (while server running).
- Separate grade page with a password-encrypted `grades.enc` (AES-GCM via browser WebCrypto; PBKDF2 250,000 iterations), component-weighted estimates. No grades outside that page.
- Minimal local JSON, atomic revisions, independent encrypted grade storage, JSON plan export/import, portable data folder (can be inside a cloud-sync folder). Open/move folders through Settings.
- Configurable guideline JSON + schema for a future external extraction agent. Includes starter study-progress indicators, not full curriculum adjudication.

## Not yet implemented / Noch offen

- Validated autonomous PDF-guidelines extraction/approval pipeline, full legal applicability and admission checks, exact seminar validation and final official graduation grade.
- Complete event reconciliation and automatic updates of previously chosen personal slots remain conservative: VVZ schedule changes are flagged, but never silently overwrite selected or manual slots. Some by-appointment or date-specific events have no weekly slot and must be handled manually.
- Cloud merge/conflict resolution between two simultaneous editing devices. **Do not edit the same cloud-synced folder from two computers at once**; sync fully before switching.
- Cloud-hosted deployment, automatic desktop installers, production accounts and hosted multi-user security. This server is **local loopback only**.
- Comprehensive unit/integration/browser test suites and continuous release/distribution.


## Feedback revision (November 2026) / Überarbeitung

- **Real study progress vs scenarios** / **Tatsächlicher Verlauf vs Szenarien**: dashboard and top semester board now show actual progress, while named hypothetical specialisation scenarios are separate below; the former is never overwritten when switching scenario.
- **Shortlist first** / **Erst Merkliste**: catalogue results can be shortlisted, then assigned from a dropdown in Semester planning. Assigned courses can be unselected without deleting their shortlist entry. The timetable add-event form selects only courses already assigned to its semester.
- **Study programme/category/term filters**: MSc CSE is default, and its official section path is distinct from the RW/CSE Bachelor; category filters support Core Courses, Electives, specialisations, case studies, semester projects, Science in Perspective, master thesis and Scientific Works (zero credits). Separate RW Bachelor admission requirements are tracked **outside** MSc ECTS. The default recent-term window is previous two / current / next. Historical same-season proxies are labeled.
- **Specialisation filters**: selected specialisations narrow VVZ section-path search; empty selection yields no specialisation results. Eligible ETH MSc core-course programmes can be searched as potentially creditable CSE electives, subject to individual recognition.
- **Required Study Achievements** on actual dashboard and per scenario: 120 total; 74 main-area credits; two core courses ≥12 ECTS; four specialisation lectures and one seminar ≥18 ECTS; two electives ≥12 ECTS; two case studies (3 ECTS each); term project 8; SiP 2; thesis 30; Scientific Works prerequisite at Bachelor/Master level, and separately selected admission conditions. Core Courses **Advanced Machine Learning** and **Probabilistic Artificial Intelligence** may not both count as cores. Figures are provisional because individual regulations and actual credit approval must be checked.
- **Graduation grade formula** from MSc-CSE Guidelines §3.3 (p. 10): `(2*core1 + 2*core2 + SUM(four specialisation lecture grades) + SUM(all included elective grades) + 4*thesis_grade) / (12 + number_of_included_electives)`. Each module's internal component grades may first be averaged by its own assessment weights. Grade values never appear outside the private grade page.
- **Actual VVZ timetable** / **Termine aus VVZAPI**: `/api/v1/course/get/{id}` gives real weekday/start/end/building/floor/room, and `/api/v1/unit/{id}/get` includes exercise groups. They are fetched into the timetable through the shared one-request-per-minute queue, with selectable timeslots and room data; API source/link, historic proxy flag, and optional CourseReview link appear on linked modules. No synthetic times are inserted into personal data.
- **Course links** / **Verlinkungen**: direct official ETH VVZ for an identified learning unit, or official VVZ number search as fallback; CourseReview links appear only if VVZAPI reports a CourseReview rating. CourseReview is not affiliated with ETH.

Run the optional browser UI regression test with `python3 tests/browser_smoke.py` (developer dependency Playwright/Chromium only). It uses mocked local responses and synthetic course data; no personal data or live API traffic.

### Limitations / Grenzen

The full Guidelines extraction agent is still a future component; a manually reviewed machine-readable rule starter is used, not a binding graduation audit. Programmatic identification of the exact *anrechenbar* course category from the student's admission ruling requires manual confirmation. VVZ timeslots missing times or listed only "by appointment" cannot be rendered as weekly recurring events. Auto-scheduling exercise groups is deliberately opt-in because group selection is personal. A public hosted edition/desktop installer is still not delivered.

## Storage / Datenspeicher

Default: `./user-data/masterplan.json` and (only if grades are saved) `./user-data/grades.enc`. Use environment variable `MASTERPLAN_DATA_DIR` before starting, or Settings → Move/Open data folder (path can be a Nextcloud/OneDrive/iCloud/Dropbox local sync folder). JSON stores personal selections rather than huge VVZ catalogues. Personal data paths are in `.gitignore`. Export and import covers study plans, **not** the grade vault. Back up both files together; loss of the grade password makes the grade vault unrecoverable. The web app is local HTTP, not automatically authenticated to any cloud service.

## VVZ data integration

- Search: `GET /api/v0/search/compact` through a local server proxy. Program matching uses the VVZAPI `offered:` section-path filter, with `title:` search and optional core/elective section filters.
- Course-number results provide semester-specific unit IDs. When the chosen semester is absent, the planner finds the latest *earlier* same-season occurrence and visibly marks it as **proxy** (never confirmed availability).
- Details endpoint support: `/api/vvz/unit/{id}` and `/api/vvz/times/{id}`. The timetable endpoint returns normalised actual VVZ course component timeslots and, once the second queued API response arrives, learning-unit exercise-group timeslots; users select which slots to add to their schedule.
- VVZAPI includes an optional CourseReview average. A CourseReview link is rendered **only when that rating actually exists**; official ETH VVZ links are shown for linked courses independently of reviews. Never invent ratings.
- Rate limiting is **one upstream request every 60 seconds globally per server process**, independent of browser tabs. The timetable loader queues requests to avoid rate-limit failures; results are cached and visible progressively, not instantaneously when many units are selected. Historic proxy slots are explicitly unconfirmed. The in-memory cache refreshes stale items after 30 minutes when requested; API changes are indicated rather than silently replacing selected slots.

The third-party [VVZAPI](https://github.com/markbeep/vvzapi) project is independent from ETH Zurich, has its own licence (GPL-3.0 for its source) and requests attribution. MasterPlan consumes the public API and does **not** bundle or modify VVZAPI source.

## Guidelines agent contract

An external agent should produce `guidelines/cse-guidelines.json` conforming to `guidelines/cse-guidelines.schema.json`. Each confidently extracted rule should include provenance (page and document source), regulation applicability and extracted text. The checked starter file has `sourceChecked: false`, and unknown data must not be invented. The app reads the configured thresholds but **does not automatically grant official academic recognition**. Do not commit private documents or personal records.

## Development / Entwicklung

Python standard library only. Run tests with `python3 -m unittest discover -s tests -v`. To adjust listening port, use `sh run.sh --port 9000`. To stay on loopback, do not change the bind address to `0.0.0.0` unless you add authentication and proper security controls. The built-in HTTP server is **not suitable for untrusted public hosting**.

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
