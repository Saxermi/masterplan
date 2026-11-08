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
- Reliable auto-population of all actual VVZ meeting times and groups (manual times work); automatic comprehensive changeset notifications to linked modules.
- Cloud merge/conflict resolution between two simultaneous editing devices. **Do not edit the same cloud-synced folder from two computers at once**; sync fully before switching.
- Cloud-hosted deployment, automatic desktop installers, production accounts and hosted multi-user security. This server is **local loopback only**.
- Comprehensive unit/integration/browser test suites and continuous release/distribution.

## Storage / Datenspeicher

Default: `./user-data/masterplan.json` and (only if grades are saved) `./user-data/grades.enc`. Use environment variable `MASTERPLAN_DATA_DIR` before starting, or Settings → Move/Open data folder (path can be a Nextcloud/OneDrive/iCloud/Dropbox local sync folder). JSON stores personal selections rather than huge VVZ catalogues. Personal data paths are in `.gitignore`. Export and import covers study plans, **not** the grade vault. Back up both files together; loss of the grade password makes the grade vault unrecoverable. The web app is local HTTP, not automatically authenticated to any cloud service.

## VVZ data integration

- Search: `GET /api/v0/search/compact` through a local server proxy. Program matching uses the VVZAPI `offered:` section-path filter, with `title:` search and optional core/elective section filters.
- Course-number results provide semester-specific unit IDs. When the chosen semester is absent, the planner finds the latest *earlier* same-season occurrence and visibly marks it as **proxy** (never confirmed availability).
- Details endpoint support: `/api/vvz/unit/{id}` and `/api/vvz/times/{id}`. Full timetable slot mapping into the UI remains a follow-up.
- Rate limiting is **one upstream request every 60 seconds globally per server process**, independent of browser tabs. Matching cached queries return immediately. This deliberately limits browsing throughput; enlarge/change the strategy only after reviewing upstream terms and API capabilities.

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
