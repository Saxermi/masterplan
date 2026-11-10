"""Offline-first VVZ catalogue cache, compatible with vvzapi.ch /api/v1/dump.

The downloaded SQLite database contains ETH catalogue data ONLY. Never place it in
MASTERPLAN_DATA_DIR, which may be a cloud-synchronised personal folder.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import zipfile
from contextlib import closing

CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_ZIP_BYTES = 2_000_000_000
MAX_SQLITE_BYTES = 4_000_000_000
REQUIRED_TABLES = {"learningunit", "course", "unitsectionlink", "sectionpathview", "rating"}


def db_connect(path):
    # A fresh, immutable, read-only connection per operation. Nothing is copied
    # into the personal data folder, and ZIP content is never executed as code.
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def validate_db(path):
    with closing(db_connect(path)) as con:
        tables = {row[0].lower() for row in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        if not REQUIRED_TABLES.issubset(tables):
            raise ValueError("VVZ dump is missing expected catalogue tables")
        if con.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
            raise ValueError("VVZ dump SQLite integrity check failed")
    return True


def prepare_db(path):
    """The upstream export has no indexes. Build these once per snapshot."""
    with closing(sqlite3.connect(path)) as con:
        con.executescript("""
            CREATE INDEX IF NOT EXISTS mp_unit_id ON learningunit(id);
            CREATE INDEX IF NOT EXISTS mp_unit_number_term ON learningunit(number, semkez DESC, id DESC);
            CREATE INDEX IF NOT EXISTS mp_unit_term ON learningunit(semkez);
            CREATE INDEX IF NOT EXISTS mp_link_section_unit ON unitsectionlink(section_id, unit_id);
            CREATE INDEX IF NOT EXISTS mp_link_unit_section ON unitsectionlink(unit_id, section_id);
            CREATE INDEX IF NOT EXISTS mp_path_id ON sectionpathview(id);
            CREATE INDEX IF NOT EXISTS mp_course_unit ON course(unit_id);
            CREATE INDEX IF NOT EXISTS mp_rating_number ON rating(course_number);
        """)


def install_zip(zip_file, target):
    """Validate ZIP and SQLite before atomically replacing a usable database."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, candidate = tempfile.mkstemp(prefix=".vvz-db-", suffix=".sqlite", dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(zip_file) as archive:
            options = [i for i in archive.infolist() if not i.is_dir() and
                       Path(i.filename).suffix.lower() in (".sqlite", ".sqlite3", ".db")]
            if not options:
                raise ValueError("VVZ dump ZIP contains no SQLite database")
            # The API ZIP normally includes a single trimmed database.
            info = max(options, key=lambda i: i.file_size)
            if info.file_size > MAX_SQLITE_BYTES or info.file_size < 1024:
                raise ValueError("Unexpected SQLite dump size")
            length = 0
            with archive.open(info) as inp, open(candidate, "wb") as out:
                while chunk := inp.read(1024 * 1024):
                    length += len(chunk)
                    if length > MAX_SQLITE_BYTES or length > info.file_size:
                        raise ValueError("VVZ decompression size exceeds limit")
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if length != info.file_size:
                raise ValueError("Incomplete SQLite database from VVZ dump")
        validate_db(candidate)
        prepare_db(candidate)
        os.replace(candidate, target)
        return length
    finally:
        if os.path.exists(candidate):
            os.unlink(candidate)


def _json_value(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value if isinstance(value, type(fallback)) else fallback
    try:
        result = json.loads(value)
        return result if isinstance(result, type(fallback)) else fallback
    except (ValueError, TypeError):
        return fallback


def _path_like(value):
    # Case-insensitive matching of programme/section terms; escape user LIKE metacharacters.
    term = value.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return "%" + term + "%"


class LocalCatalog:
    def __init__(self, filename, degrees, category_paths, eligible_core_programmes, specialisations):
        self.filename = Path(filename)
        self.lock = threading.RLock()  # coordinate Windows file replacement with active readers
        self.degrees = degrees
        self.category_paths = category_paths
        self.eligible_cores = eligible_core_programmes
        self.specialisations = specialisations
        self._prepared = None

    def available(self):
        return self.filename.is_file()

    def _ensure_indexes(self):
        # Upgrade old installed snapshots too, without downloading them again.
        stat = self.filename.stat()
        signature = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if signature != self._prepared:
            prepare_db(self.filename)
            stat = self.filename.stat()
            self._prepared = (stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def _path_filter(self, terms, params):
        """Programme roots and specialisation segments must not match substrings."""
        predicates = []
        for term in terms:
            columns = ("LOWER(COALESCE(p.path_en,''))", "LOWER(COALESCE(p.path_de,''))")
            if term in self.degrees.values():
                exact = term.lower()
                pattern = _path_like(term)[1:-1] + " > %"
                predicates.append("(" + " OR ".join(f"({col}=? OR {col} LIKE ? ESCAPE '\\')" for col in columns) + ")")
                params.extend([exact, pattern, exact, pattern])
            elif term in self.specialisations:
                pattern = "% > " + _path_like(term)[1:-1]
                predicates.append("(" + " OR ".join(f"({col} LIKE ? ESCAPE '\\' OR {col} LIKE ? ESCAPE '\\')" for col in columns) + ")")
                params.extend([pattern, pattern + " > %", pattern, pattern + " > %"])
            else:
                params.extend([_path_like(term), _path_like(term)])
                predicates.append("(" + " OR ".join(f"{col} LIKE ? ESCAPE '\\'" for col in columns) + ")")
        return " AND ".join(predicates)

    def search(self, query, programme, category, specialisations, semester, window, limit, offset, select_offering):
        if not self.available():
            raise FileNotFoundError("VVZ dump has not been downloaded")
        if programme not in self.degrees:
            raise ValueError("Unknown programme")
        if category not in ("", "eligible-core", *self.category_paths):
            raise ValueError("Unknown category")
        if category == "eligible-core":
            if programme == "eligible-core-all":
                scope = sorted(set(self.degrees[p] for p in self.eligible_cores))
            elif programme in self.eligible_cores:
                scope = [self.degrees[programme]]
            else:
                raise ValueError("Select an eligible MSc programme")
            section_variants = [[path, "core courses"] for path in scope]
        else:
            if programme == "eligible-core-all":
                raise ValueError("Select core-course elective filter")
            path = self.degrees["cse-bsc"] if programme == "cse" and category == "requirement" else self.degrees[programme]
            paths = self.category_paths.get(category) or [""]
            if category == "specialisation" and specialisations:
                if any(name not in self.specialisations for name in specialisations):
                    raise ValueError("Unknown specialisation")
                section_variants = [[part for part in (path, cat, name) if part]
                                    for cat in paths for name in specialisations]
            else:
                section_variants = [[part for part in (path, cat) if part] for cat in paths]
        if category == 'sip':
            section_variants = [['science in perspective']]
        if category == 'scientific':
            section_variants = []
        if category == "specialisation" and not specialisations:
            return {"results": [], "total": 0, "upstreamTotal": 0, "source": "local-dump",
                    "recentSemesters": window, "eligibleCoreElective": False}
        terms = window if semester == 'recent' else semester.split(',')
        if not 1 <= len(terms) <= 5 or any(not re.fullmatch(r'\d{4}[SW]', t) for t in terms):
            raise ValueError('Invalid semester selection')
        filters = ["u.number IS NOT NULL", "u.semkez IN (" + ','.join('?' for _ in terms) + ")"]
        values = list(terms)
        if category == 'scientific':
            filters.append("u.number IN ('401-2000-00L','402-2000-00L')")
        # Resolve section paths once, then use the section->unit index. A
        # correlated path scan for every learning unit is prohibitively slow.
        scope_sql = []
        scope_values = []
        for terms in section_variants:
            if terms:
                scope_sql.append("(" + self._path_filter(terms, scope_values) + ")")
        if scope_sql:
            filters.append("u.id IN (SELECT l.unit_id FROM unitsectionlink l WHERE l.section_id IN "
                           "(SELECT p.id FROM sectionpathview p WHERE " + " OR ".join(scope_sql) + "))")
            values.extend(scope_values)
        q = query.strip()[:120]
        if q:
            if len(q) > 3 and q[:3].isdigit() and "-" in q:
                filters.append("LOWER(u.number) LIKE ? ESCAPE '\\'")
                values.append(_path_like(q))
            else:
                # Word-wise search tolerates the official abbreviated CSE title.
                q = q.lower().replace("computational science and engineering", "cse")
                for word in q.split():
                    filters.append("(LOWER(COALESCE(u.title,'')) LIKE ? ESCAPE '\\' OR "
                                   "LOWER(COALESCE(u.title_english,'')) LIKE ? ESCAPE '\\')")
                    values.extend([_path_like(word), _path_like(word)])
        where = " AND ".join(filters)
        with self.lock:
            self._ensure_indexes()
            with closing(db_connect(self.filename)) as con:
                rows = con.execute("SELECT u.id,u.number,u.semkez,u.title,u.title_english,u.credits,u.levels,u.language "
                                   "FROM learningunit u WHERE " + where + " ORDER BY u.semkez DESC,u.id DESC", values).fetchall()
                grouped = {}
                for row in rows:
                    grouped.setdefault(row["number"], []).append(row)
                numbers = sorted(grouped, key=lambda n: ((grouped[n][0]["title_english"] or grouped[n][0]["title"] or n).lower(), n))
                total = len(numbers)
                results = []
                for number in numbers[offset:offset + limit]:
                    records = grouped[number]
                    semesters = {}
                    for r in records:
                        semesters.setdefault(r["semkez"], r["id"])
                    wanted = max(semesters)
                    offering = select_offering(semesters, wanted) if wanted else None
                    if not offering or not offering.get("unit_id"):
                        continue
                    rec = next(r for r in records if r["id"] == offering["unit_id"])
                    rating = con.execute("SELECT (recommended+engaging+difficulty+effort+resources)/5.0 "
                                         "FROM rating WHERE course_number=?", (number,)).fetchone()
                    origins = []
                    if category == 'eligible-core':
                        for path in scope:
                            args = []
                            predicate = self._path_filter([path, 'core courses'], args)
                            ids = list(semesters.values())
                            if con.execute("SELECT 1 FROM unitsectionlink l JOIN sectionpathview p ON p.id=l.section_id WHERE l.unit_id IN (" + ','.join('?' for _ in ids) + ") AND " + predicate + " LIMIT 1", [*ids, *args]).fetchone():
                                origins.append(path)
                    results.append({"coreProgrammes": origins, "number": number, "title": rec["title"], "title_english": rec["title_english"],
                                    "credits": rec["credits"], "levels": _json_value(rec["levels"], []),
                                    "language": rec["language"], "rating": round(rating[0], 2) if rating and rating[0] is not None else None,
                                    "semesters": semesters, "offering": offering})
                return {"results": results, "total": total, "upstreamTotal": total, "source": "local-dump",
                        "recentSemesters": window, "eligibleCoreElective": category == "eligible-core"}

    def unit(self, unit_id):
        with self.lock:
            self._ensure_indexes()
        with self.lock, closing(db_connect(self.filename)) as con:
            r = con.execute("SELECT * FROM learningunit WHERE id=?", (unit_id,)).fetchone()
            if r is None:
                return None
            result = dict(r)
            for name in ("groups", "levels", "departments", "primary_target_group"):
                if name in result:
                    result[name] = _json_value(result[name], [])
            return result

    def meetings(self, unit_id):
        with self.lock:
            self._ensure_indexes()
        with self.lock, closing(db_connect(self.filename)) as con:
            rows = con.execute("SELECT number,title,timeslots FROM course WHERE unit_id=? ORDER BY number", (unit_id,)).fetchall()
            return [{"number": r["number"], "title": r["title"], "timeslots": _json_value(r["timeslots"], [])}
                    for r in rows]


class VvzDump:
    """Metadata-checked, on-disk SQLite dump; the upstream client enforces global limits."""
    def __init__(self, directory, upstream, catalog, clock=time.time):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.upstream = upstream
        self.catalog = catalog
        self.clock = clock
        self.lock = threading.RLock()
        self.running = False
        self.error = None
        self.phase = "ready" if catalog.available() else "missing"
        self.metadata_file = self.directory / "metadata.json"
        try:
            self.metadata = json.loads(self.metadata_file.read_text(encoding="utf-8"))
            if not isinstance(self.metadata, dict):
                self.metadata = {}
        except (OSError, ValueError):
            self.metadata = {}

    def status(self):
        with self.lock:
            return {"available": self.catalog.available(), "phase": self.phase, "checking": self.running,
                    "lastChecked": self.metadata.get("lastChecked", 0), "lastUpdated": self.metadata.get("lastUpdated", 0),
                    "size": self.catalog.filename.stat().st_size if self.catalog.available() else 0,
                    "error": self.error, "maxRequestsPerMinute": 1, "checkIntervalHours": CHECK_INTERVAL_SECONDS // 3600,
                    "storage": str(self.directory)}

    def check(self, force=False):
        with self.lock:
            if self.running:
                return self.status()
            if not force and self.catalog.available() and self.clock() - self.metadata.get("lastChecked", 0) < CHECK_INTERVAL_SECONDS:
                return self.status()
            self.running = True
            self.phase = "checking"
            self.error = None
            threading.Thread(target=self._refresh, daemon=True, name="masterplan-vvz-dump").start()
            return self.status()

    def _write_metadata(self):
        fd, name = tempfile.mkstemp(prefix=".metadata-", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                json.dump(self.metadata, fp, separators=(",", ":"))
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(name, self.metadata_file)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _refresh(self):
        zip_path = self.directory / ".download.zip"
        try:
            remote, _ = self.upstream.get("https://vvzapi.ch/api/v1/dump/metadata", wait=True, force=True)
            if not isinstance(remote, dict) or not isinstance(remote.get("size_in_bytes"), int) or not isinstance(remote.get("last_modified_ms"), int):
                raise ValueError("Unexpected VVZ dump metadata")
            current = {"size_in_bytes": remote["size_in_bytes"], "last_modified_ms": remote["last_modified_ms"]}
            if not (self.catalog.available() and self.metadata.get("remote") == current):
                with self.lock:
                    self.phase = "downloading"
                self.upstream.download("https://vvzapi.ch/api/v1/dump", zip_path, max_bytes=MAX_ZIP_BYTES)
                if zip_path.stat().st_size != current["size_in_bytes"]:
                    raise ValueError("Downloaded VVZ dump size does not match metadata")
                with self.lock:
                    self.phase = "validating"
                # Do not replace a working database before validation succeeds.
                with self.catalog.lock:
                    install_zip(zip_path, self.catalog.filename)
                self.metadata["remote"] = current
                self.metadata["lastUpdated"] = self.clock()
            self.metadata["lastChecked"] = self.clock()
            self._write_metadata()
            with self.lock:
                self.phase = "ready"
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.phase = "stale" if self.catalog.available() else "failed"
        finally:
            try:
                zip_path.unlink(missing_ok=True)
            except OSError:
                pass
            with self.lock:
                self.running = False
