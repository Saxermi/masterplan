"""MasterPlan: local-only HTTP application with atomic portable storage and VVZ proxy."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from vvz_schedule import parse_official_courses
from vvz_dump import LocalCatalog, VvzDump, MAX_ZIP_BYTES

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
DEFAULT_DATA = Path(os.environ.get("MASTERPLAN_DATA_DIR", str(BASE / "user-data"))).expanduser().resolve()
MAX_BODY = 2 * 1024 * 1024
CATALOG_BASE = "https://vvzapi.ch"
DEGREES = {
    "cse": "computational science and engineering master",
    "cse-bsc": "computational science and engineering bachelor",
    "mathematics-bsc": "mathematics bachelor",
    "mathematics-msc": "mathematics master",
    "physics-bsc": "physics bachelor",
    "physics-msc": "physics master",
    "computer-science-msc": "computer science master",
    "statistics-msc": "statistics master",
    "data-science-msc": "data science master",
    "applied-mathematics-msc": "mathematics master",  # ETH VVZ groups pure/applied under Mathematics Master
    "neural-systems-msc": "neural systems and computation master",
    "robotics-msc": "robotics, systems and control master",
    "electrical-engineering-msc": "electrical engineering and information technology master",
    "eligible-core-all": "",  # all automatically eligible ETH MSc core courses
    "all": "",
}


# ETH MSc CSE Guidelines 2024, §3.6 (July 2026 edition), page 19:
# Core Courses (NOT general electives) from the programmes below can be selected
# as CSE electives without prior permission; double counting and bachelor credit
# recognition rules still apply. The two Mathematics programmes share a VVZ tree.
# Guidelines-agent output is the source of truth; updates apply after a restart.
ELIGIBLE_CORE_PROGRAMMES = frozenset(json.loads(
    (BASE / "guidelines" / "cse-guidelines.json").read_text(encoding="utf-8")
).get("electiveEligibility", {}).get("coreCourseProgrammeKeys", []))


# Section names are part of ETH VVZ paths, not the course title. Use OR for
# different historical naming conventions, then filter the offered semesters.
SPECIALISATIONS = frozenset(("Astrophysics", "Biology", "Chemistry", "Computational Finance", "Electromagnetics", "Fluid Dynamics", "Geophysics", "Physics", "Physics of the Atmosphere", "Robotics", "Systems and Control"))

CATEGORY_PATHS = {
    "core": ["core courses"],
    "elective": ["electives"],
    "specialisation": ["field of specialization", "fields of specialization", "specialisation"],
    "case": ["case studies"],
    "project": ["semester project", "term project", "semester thesis", "semester paper"],
    "sip": ["science in perspective"],
    "thesis": ["master thesis", "master's thesis"],
    "scientific": ["scientific works"],
    "requirement": [],  # Admission requirements are personal, not a VVZ category.
}


def recent_semesters(now=None):
    """Last two + current + next two ETH semesters, Europe/Zurich."""
    now = now or datetime.now(ZoneInfo("Europe/Zurich"))
    year, month = now.year, now.month
    current = f"{year if month >= 2 else year - 1}{'W' if month >= 9 or month == 1 else 'S'}"
    terms = []
    for y in range(year - 3, year + 3):
        terms.extend([f"{y}S", f"{y}W"])
    i = terms.index(current)
    return terms[i - 2:i + 3]


def build_catalog_query(query, programme, category, specialisations=None):
    """VVZAPI query restricted to official programme section paths."""
    if programme not in DEGREES:
        raise ValueError("Unknown programme")
    if category not in ("", "eligible-core", *CATEGORY_PATHS):
        raise ValueError("Unknown course category")
    clean = query.strip()[:120].replace('"', '').replace('`', '')
    if category == "eligible-core":
        if programme == "eligible-core-all":
            distinct_paths = sorted({DEGREES[p] for p in ELIGIBLE_CORE_PROGRAMMES})
            clause = "(" + " OR ".join(f'(o:"{p}" o:"core courses")' for p in distinct_paths) + ")"
        elif programme in ELIGIBLE_CORE_PROGRAMMES:
            clause = f'o:"{DEGREES[programme]}" o:"core courses"'
        else:
            raise ValueError("Select an eligible MSc programme for CSE core-course electives")
        field = "number" if re.match(r"^\d{3}-[0-9A-Za-z-]+$", clean) else "title"
        return " ".join([clause, f'{field}:"{clean}"' if clean else ""]).strip()
    if programme == "eligible-core-all":
        raise ValueError("Choose the CSE-elective core-course category")
    # Entry requirements from an admission letter are generally RW/CSE BSc units.
    # Do not claim that *all* BSc units are individual admission requirements.
    degree = DEGREES["cse-bsc"] if programme == "cse" and category == "requirement" else DEGREES[programme]
    clause = f'o:"{degree}"' if degree else ""
    paths = CATEGORY_PATHS.get(category, [])
    if paths:
        path_filter = "(" + " OR ".join(f'o:"{part}"' for part in paths) + ")" if len(paths) > 1 else f'o:"{paths[0]}"'
        clause = f"{clause} {path_filter}".strip()
    if clean:
        field = "number" if re.match(r"^\d{3}-[0-9A-Za-z-]+$", clean) else "title"
        clause = f'{clause} {field}:"{clean}"'.strip()
    if category == "specialisation" and specialisations:
        selected = list(dict.fromkeys(specialisations))
        if any(x not in SPECIALISATIONS for x in selected):
            raise ValueError("Unknown specialisation")
        if len(selected) > len(SPECIALISATIONS):
            raise ValueError("Too many specialisations")
        selection = " OR ".join(f'o:"{x.lower()}"' for x in selected)
        clause = f'{clause} ({selection})'.strip()
    if not clause:
        raise ValueError("Provide a search term or choose a programme")
    return clause


def default_actual():
    return {"id": "actual", "name": "Mein tatsächliches Studium", "specialisation": "",
            "semesters": ["2026W", "2027S", "2027W", "2028S"],
            "lockedSemesters": [], "courses": [], "notes": ""}


def initial_state():
    return {
        "schema": 2,
        "revision": 0,
        "language": "de",
        "theme": "light",
        "activePlan": "actual",
        "actualPlan": default_actual(),
        "interests": [],
        "scientificWorksBSc": False,
        "selectedSpecialisations": ["Physics", "Fluid Dynamics"],
        "history": [],
        "plans": [
            {"id": "physics", "name": "Physics Specialisation", "specialisation": "Physics", "semesters": ["2026W", "2027S", "2027W", "2028S"], "lockedSemesters": [], "courses": [], "notes": ""},
            {"id": "fluids", "name": "Fluid Dynamics Specialisation", "specialisation": "Fluid Dynamics", "semesters": ["2026W", "2027S", "2027W", "2028S"], "lockedSemesters": [], "courses": [], "notes": ""},
        ],
    }


def migrate_state(x):
    """Backward-compatible, non-destructive schema-v1 upgrade; scenarios stay scenarios."""
    if not isinstance(x, dict):
        raise ValueError("Invalid state")
    if x.get("schema") == 1:
        x = copy.deepcopy(x)
        x["schema"] = 2
        x["actualPlan"] = default_actual()
        x["activePlan"] = "actual"
        x["interests"] = []
        x["scientificWorksBSc"] = False
        for plan in x['plans']:
            for course in plan.get('courses', []):
                course.setdefault('ects', 0)
                course.setdefault('status', 'planned')
                course.setdefault('events', [])
                course.setdefault('title', '')
                if course.get('role') == 'eligible-core':
                    course['role'] = 'elective'
        for course in x.get('history', []):
            course.setdefault('ects', 0)
            course.setdefault('status', 'completed')
            course.setdefault('events', [])
            course.setdefault('title', '')
    return x


def _text(value, maximum, nonempty=False):
    return isinstance(value, str) and len(value) <= maximum and (not nonempty or bool(value.strip()))


def _credits(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 40


def _term(value):
    return isinstance(value, str) and re.fullmatch(r"\d{4}[SW]", value) is not None


def _private_grade_keys(value):
    if isinstance(value, dict):
        return any('grade' in str(k).lower() or 'notevalue' in str(k).lower() or _private_grade_keys(v) for k, v in value.items())
    return isinstance(value, list) and any(_private_grade_keys(v) for v in value)


def valid_event(event):
    if not isinstance(event, dict) or type(event.get('day')) is not int or not 0 <= event['day'] <= 6:
        return False
    if any(not isinstance(event.get(k), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', event[k]) for k in ('start', 'end')):
        return False
    if event['start'] >= event['end']:
        return False
    if any(k in event and not _text(event[k], 100) for k in ('building', 'floor', 'room')):
        return False
    if event.get('date') is not None and not _text(event['date'],10):
        return False
    if event.get('date'):
        try:
            datetime.strptime(event['date'], '%Y-%m-%d')
        except (TypeError, ValueError):
            return False
    return all(k not in event or type(event[k]) is bool for k in ('biweekly', 'firstHalf', 'secondHalf'))


def valid_course(course):
    if not isinstance(course, dict) or not _text(course.get('id'), 150, True) or not _term(course.get('semester')):
        return False
    if not _text(course.get('title', ''), 250) or not _text(course.get('number', ''), 60) or not _credits(course.get('ects')):
        return False
    if course.get('role') not in (*CATEGORY_PATHS, 'extra') or course.get('status') not in ('interested', 'planned', 'enrolled', 'completed'):
        return False
    if any(k in course and type(course[k]) is not bool for k in ('locked', 'proxy', 'reviewAvailable', 'usedForBSc')):
        return False
    if course.get('creditApproved') is not None and type(course['creditApproved']) is not bool:
        return False
    if course.get('subtype') not in (None, 'lecture', 'seminar') or not _text(course.get('specialisation', ''), 150):
        return False
    if course.get('unitId') is not None and (type(course['unitId']) is not int or not 1 <= course['unitId'] <= 1_000_000_000):
        return False
    if course.get('sourceSemester') is not None and not _term(course['sourceSemester']):
        return False
    events = course.get('events')
    return isinstance(events, list) and len(events) <= 100 and all(valid_event(e) for e in events)


def valid_state(x):
    """Validate storage shape; incomplete academic plans remain valid drafts."""
    if not isinstance(x, dict) or type(x.get('revision')) is not int or x['revision'] < 0 or x.get('schema') != 2:
        return False
    if _private_grade_keys(x) or x.get('language') not in ('de', 'en') or x.get('theme') not in ('light', 'dark'):
        return False
    if type(x.get('scientificWorksBSc')) is not bool:
        return False
    for key, maximum in [('plans', 100), ('history', 500), ('interests', 500), ('selectedSpecialisations', len(SPECIALISATIONS))]:
        if not isinstance(x.get(key), list) or len(x[key]) > maximum:
            return False
    specs = x['selectedSpecialisations']
    if any(not isinstance(s, str) or s not in SPECIALISATIONS for s in specs) or len(set(specs)) != len(specs):
        return False
    if not all(valid_course(c) and c['status']=='completed' for c in x['history']) or len({c['id'] for c in x['history']}) != len(x['history']):
        return False
    for interest in x['interests']:
        if not isinstance(interest, dict) or not _text(interest.get('id'), 150, True) or not _text(interest.get('title', ''), 250):
            return False
        if 'ects' in interest and not _credits(interest['ects']):
            return False
        if not _text(interest.get('number', ''), 60) or interest.get('suggestedRole', 'extra') not in (*CATEGORY_PATHS, 'extra', 'specialisation-seminar'):
            return False
        offerings = interest.get('offerings', {})
        if not isinstance(offerings, dict) or len(offerings) > 100 or any(not _term(k) or type(v) is not int or not 1 <= v <= 1_000_000_000 for k, v in offerings.items()):
            return False
    if len({c['id'] for c in x['interests']}) != len(x['interests']):
        return False
    actual = x.get('actualPlan')
    if not isinstance(actual, dict) or actual.get('id') != 'actual':
        return False
    ids = set()
    for plan in [actual, *x['plans']]:
        if not isinstance(plan, dict) or not _text(plan.get('id'), 150, True) or not _text(plan.get('name'), 150):
            return False
        if plan['id'] in ids or any(not isinstance(plan.get(k), list) for k in ('courses', 'semesters', 'lockedSemesters')):
            return False
        ids.add(plan['id'])
        terms, locked = plan['semesters'], plan['lockedSemesters']
        if len(plan['courses']) > 300 or len(terms) > 30 or any(not _term(s) for s in terms + locked):
            return False
        if len(set(terms)) != len(terms) or len(set(locked)) != len(locked) or not set(locked).issubset(terms):
            return False
        if any(not valid_course(c) or c['semester'] not in terms for c in plan['courses']):
            return False
        if len({c['id'] for c in plan['courses']}) != len(plan['courses']):
            return False
    return isinstance(x.get('activePlan'), str) and x['activePlan'] in ids


class Store:
    def __init__(self, folder=DEFAULT_DATA):
        self.lock = threading.RLock()
        self.folder = Path(folder).expanduser().resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _ensure(self):
        if not (self.folder / "masterplan.json").exists():
            self._atomic(self.folder / "masterplan.json", initial_state())

    @staticmethod
    def _atomic(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".masterplan-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(value, out, ensure_ascii=False, separators=(",", ":"))
                out.flush()
                os.fsync(out.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def get(self):
        with self.lock:
            file = self.folder / "masterplan.json"
            raw = json.loads(file.read_text(encoding="utf-8"))
            new = migrate_state(raw)
            if new is not raw:
                if not valid_state(new):
                    raise ValueError("Invalid legacy study data")
                self._atomic(file, new)
            return new

    def save(self, incoming):
        with self.lock:
            old = self.get()
            if not valid_state(incoming):
                raise ValueError("Invalid MasterPlan data format")
            if incoming.get("revision") != old["revision"]:
                raise RuntimeError("Revision conflict: reload before saving")
            previous = { (p['id'], c['id']): c for p in [old['actualPlan'], *old['plans']] for c in p['courses'] }
            for plan in [incoming['actualPlan'], *incoming['plans']]:
                for course in plan['courses']:
                    before = previous.get((plan['id'], course['id']))
                    if course.get('unitId') and course.get('sourceSemester') != course['semester']:
                        if not before or any(before.get(k) != course.get(k) for k in ('semester', 'unitId', 'sourceSemester')):
                            raise ValueError('Course is not offered in the selected semester')
            new = copy.deepcopy(incoming)
            new["revision"] = old["revision"] + 1
            self._atomic(self.folder / "masterplan.json", new)
            return new

    def move(self, requested):
        with self.lock:
            target = Path(requested).expanduser().resolve()
            if not target.is_absolute() or target == Path(target.anchor) or target == BASE:
                raise ValueError("Select a dedicated data folder")
            target.mkdir(parents=True, exist_ok=True)
            source = self.folder
            if source == target:
                return str(target)
            if (target / "masterplan.json").exists():
                raise FileExistsError("Folder already contains MasterPlan data. Open it instead of overwriting")
            for name in ("masterplan.json", "grades.enc"):
                if (source / name).exists():
                    shutil.copy2(source / name, target / name)
            self.folder = target
            return str(target)

    def open_folder(self, requested):
        with self.lock:
            target = Path(requested).expanduser().resolve()
            state_file = target / "masterplan.json"
            if not state_file.is_file() or not valid_state(migrate_state(json.loads(state_file.read_text(encoding="utf-8")))):
                raise ValueError("No valid MasterPlan data in selected folder")
            self.folder = target
            return str(target)


class UpstreamRateLimit:
    """One shared reservation every 60 seconds: at most one VVZAPI request/minute.

    Metadata checks, whole database ZIPs and live fallback calls share this gate.
    """
    def __init__(self, interval=60.0):
        self.lock = threading.RLock()
        self.interval = interval
        # A first request must be permitted even on systems booted <60s ago.
        self.last_request = -self.interval

    def acquire(self, wait=False):
        while True:
            with self.lock:
                delay = self.interval - (time.monotonic() - self.last_request)
                if delay <= 0:
                    self.last_request = time.monotonic()
                    return
            if not wait:
                raise RuntimeError(f"VVZ rate limit: retry in {int(delay) + 1}s")
            time.sleep(min(delay, 2))


class VvzCache:
    """Fallback API requests, plus shared upstream gate for the persistent dump."""

    def __init__(self, folder, rate=None):
        self.lock = threading.RLock()
        self.cache = {}
        self.pending = []
        self.processing = None
        self.failures = {}
        self.worker_running = False
        self.folder = Path(folder)
        self.rate = rate or UpstreamRateLimit()

    def _schedule_file(self, url):
        if urlsplit(url).hostname == 'www.vvz.ethz.ch':
            return self.folder / 'schedules' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
        return None

    def _read_schedule(self, url):
        file = self._schedule_file(url)
        if file and file.exists():
            try:
                value = json.loads(file.read_text(encoding='utf-8'))
                if isinstance(value, dict) and isinstance(value.get('courses'), list) and isinstance(value.get('checked'), (int, float)):
                    return value
            except (ValueError, OSError):
                pass
        return None

    def get(self, url, wait=False, force=False):
        with self.lock:
            now = time.monotonic()
            entry = self.cache.get(url)
            if entry and now - entry[0] < 1800 and not force:
                return entry[1], "cached"
        try:
            self.rate.acquire(wait=wait)
        except RuntimeError:
            if entry and not force:
                return entry[1], "stale"
            raise
        request = Request(url, headers={"User-Agent": "MasterPlan-study-planner/0.2 (+https://github.com/Saxermi/masterplan)", "Accept": "text/html" if self._schedule_file(url) else "application/json"})
        try:
            with urlopen(request, timeout=20) as response:
                if int(response.headers.get("Content-Length", "0")) > 4_000_000:
                    raise ValueError("Upstream response too large")
                raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise ValueError("Upstream response too large")
                if self._schedule_file(url):
                    result = parse_official_courses(raw.decode('utf-8'))
                    Store._atomic(self._schedule_file(url), {'checked': time.time(), 'courses': result})
                else:
                    result = json.loads(raw)
                if not isinstance(result, (dict, list)):
                    raise ValueError("Unexpected upstream response")
                with self.lock:
                    self.cache[url] = (time.monotonic(), result)
                    if len(self.cache) > 450:
                        oldest = min(self.cache, key=lambda k: self.cache[k][0])
                        self.cache.pop(oldest, None)
                return result, "live"
        except (OSError, ValueError) as exc:
            if entry and not force:
                return entry[1], "stale"
            raise RuntimeError(f"VVZ unavailable: {exc}") from exc

    def download(self, url, target, max_bytes=MAX_ZIP_BYTES):
        """Stream large dump to a temp file; never buffer it in process memory."""
        self.rate.acquire(wait=True)
        request = Request(url, headers={"User-Agent": "MasterPlan-study-planner/0.2 (+https://github.com/Saxermi/masterplan)", "Accept": "application/zip"})
        count = 0
        try:
            with urlopen(request, timeout=180) as response, open(target, "wb") as out:
                if int(response.headers.get("Content-Length", "0")) > max_bytes:
                    raise ValueError("VVZ dump exceeds the configured limit")
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > max_bytes:
                        raise ValueError("VVZ dump exceeds the configured limit")
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            return count
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Cannot download VVZ dump: {exc}") from exc

    def scheduled(self, url):
        """Nonblocking API fallback; a single worker drains requests behind the gate."""
        with self.lock:
            disk = self._read_schedule(url)
            cached = self.cache.get(url)
            if not cached and disk:
                age = max(0, time.time() - disk.get('checked', 0))
                cached = (time.monotonic() - age, disk['courses'])
                self.cache[url] = cached
            if cached:
                if time.monotonic() - cached[0] >= (86400 if disk else 1800) and url not in self.pending and self.processing != url:
                    if len(self.pending) < 100:
                        self.pending.append(url)
                        if not self.worker_running:
                            self.worker_running = True
                            threading.Thread(target=self._run_queue, daemon=True, name="masterplan-vvz-queue").start()
                return cached[1], "ready", "cached"
            if url in self.failures:
                failed_at, message = self.failures[url]
                if time.monotonic() - failed_at < 60:
                    return None, "failed", message
                del self.failures[url]
            if url not in self.pending and self.processing != url:
                if len(self.pending) >= 100:
                    return None, "failed", "VVZ request queue full"
                self.pending.append(url)
            if not self.worker_running:
                self.worker_running = True
                threading.Thread(target=self._run_queue, daemon=True, name="masterplan-vvz-queue").start()
            return None, "queued", "pending"

    def _run_queue(self):
        while True:
            with self.lock:
                if not self.pending:
                    self.processing = None
                    self.worker_running = False
                    return
                url = self.pending.pop(0)
                self.processing = url
            try:
                self.get(url, wait=True)
            except RuntimeError as exc:
                with self.lock:
                    self.failures[url] = (time.monotonic(), str(exc))
            finally:
                with self.lock:
                    self.processing = None

def normalize_meetings(courses):
    """Extract real weekly VVZ course slots. Keep source flags and avoid made-up times.

    VVZAPI: GET /api/v1/course/get/{unit_id}, Course.timeslots = TimeSlot[];
    TimeSlot has weekday 0..6, start_time/end_time, building/floor/room,
    date, first_half_semester, second_half_semester and biweekly.
    """
    if not isinstance(courses, list):
        raise ValueError("Invalid VVZ timetable response")
    normalized = []
    for course in courses:
        if not isinstance(course, dict):
            continue
        label = str(course.get("title") or course.get("number") or "Course")[:140]
        course_number = str(course.get("number") or "")[:50]
        for slot in (course.get("timeslots") or []):
            if not isinstance(slot, dict):
                continue
            try:
                day = int(slot.get("weekday"))
            except (ValueError, TypeError):
                continue
            start, end = slot.get("start_time"), slot.get("end_time")
            if not (0 <= day <= 6 and isinstance(start, str) and isinstance(end, str)
                    and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", start)
                    and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", end) and start < end):
                continue
            room = {k: str(slot.get(k) or "")[:100] for k in ("building", "floor", "room")}
            item = {"day": day, "start": start, "end": end, **room,
                    "label": label, "courseNumber": course_number,
                    "date": str(slot.get("date") or "")[:24],
                    "biweekly": bool(slot.get("biweekly")),
                    "firstHalf": bool(slot.get("first_half_semester")),
                    "secondHalf": bool(slot.get("second_half_semester")),
                    "note": str(course.get("comment") or "")[:1500]}
            # Stable slot identity ensures previously selected slots can be retained.
            item["slotKey"] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()[:20]
            normalized.append(item)
    return normalized


def sem_label(code):
    return ("FS " if code.endswith("S") else "HS ") + code[:4]


def select_offering(semesters, wanted, cutoff=None):
    """Prefer exact semester; otherwise use closest previous same-season offering."""
    if wanted in semesters:
        return {"unit_id": semesters[wanted], "source_semester": wanted, "proxy": False}
    cutoff = cutoff or recent_semesters()[0]
    earlier = [s for s in semesters if re.fullmatch(r"\d{4}[SW]", s) and s.endswith(wanted[-1]) and s < wanted and s >= cutoff]
    if not earlier:
        return {"unit_id": None, "source_semester": None, "proxy": False}
    source = max(earlier)
    return {"unit_id": semesters[source], "source_semester": source, "proxy": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "MasterPlan/0.1"

    def log_message(self, fmt, *args):
        if os.environ.get("MASTERPLAN_DEBUG") == "1":
            super().log_message(fmt, *args)

    def headers_common(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def respond(self, status, value):
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.headers_common()
        self.send_header("Content-Length", str(len(body)))
        try:
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # A closed browser connection is not a second application error.
            self.close_connection = True

    def allowed_host(self):
        host = self.headers.get("Host", "").split(":")[0].lower()
        return host in ("localhost", "127.0.0.1", "127.0.0.2", "[::1]")

    def get_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > MAX_BODY:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if not self.allowed_host():
            return self.respond(403, {"error": "Local access only"})
        parsed = urlsplit(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        if path == "/api/state":
            return self.respond(200, self.server.store.get())
        if path == "/api/storage":
            return self.respond(200, {"folder": str(self.server.store.folder)})
        if path == "/api/guidelines":
            path_rules = BASE / "guidelines" / "cse-guidelines.json"
            return self.respond(200, json.loads(path_rules.read_text(encoding="utf-8")))
        if path == "/api/grades":
            file = self.server.store.folder / "grades.enc"
            return self.respond(200, {"encrypted": json.loads(file.read_text(encoding="utf-8")) if file.exists() else None})
        if path == "/api/export":
            return self.respond(200, self.server.store.get())
        if path == "/api/vvz/dump/status":
            return self.respond(200, self.server.vvz_dump.status())
        if path == "/api/vvz/search":
            try:
                query = params.get("q", [""])[0].strip()[:120]
                programme = params.get("programme", ["cse"])[0]
                category = params.get("category", [""])[0]
                semester = params.get("semester", [""])[0]
                selected_specs = [x for x in params.get("spec", [""])[0].split("|") if x]
                vvz_query = build_catalog_query(query, programme, category, selected_specs)
                if semester != "recent" and not re.fullmatch(r"\d{4}[SW](?:,\d{4}[SW])?", semester):
                    raise ValueError("Invalid semester")
                limit = min(60, max(1, int(params.get("limit", ["40"])[0])))
                offset = max(0, min(10000, int(params.get("offset", ["0"])[0])))
                window = recent_semesters()
                if self.server.catalog.available():
                    result = self.server.catalog.search(query, programme, category, selected_specs,
                                                        semester, window, limit, offset, select_offering)
                    result["query"] = vvz_query
                    return self.respond(200, result)
                status = self.server.vvz_dump.status()
                return self.respond(503, {"error": "Der lokale VVZ-Katalog wird vorbereitet. Bitte den Status unter Einstellungen prüfen und die Suche danach erneut starten.",
                                          "code": "catalog_unavailable", "dump": status})
            except (ValueError, TypeError) as exc:
                return self.respond(400, {"error": str(exc)})
            except (RuntimeError, OSError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path.startswith("/api/vvz/unit/"):
            try:
                unit_id = int(path.rsplit("/", 1)[-1])
                if not (1 <= unit_id <= 1_000_000_000):
                    raise ValueError("Invalid unit id")
                if self.server.catalog.available():
                    data, source = self.server.catalog.unit(unit_id), "local-dump"
                    if data is None:
                        return self.respond(404, {"error": "Unit not present in local dump"})
                else:
                    data, source = self.server.vvz.get(f"{CATALOG_BASE}/api/v1/unit/{unit_id}/get")
                return self.respond(200, {"unit": data, "source": source})
            except (RuntimeError, ValueError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path.startswith("/api/vvz/times/"):
            try:
                unit_id = int(path.rsplit("/", 1)[-1])
                if not 1 <= unit_id <= 1_000_000_000:
                    raise ValueError("Invalid unit id")
                if self.server.catalog.available():
                    data = self.server.catalog.meetings(unit_id)
                    unit = self.server.catalog.unit(unit_id)
                    if unit is None:
                        return self.respond(404, {"error": "Unit not present in local dump"})
                    meetings = normalize_meetings(data)
                    groups = [{"title": "Group: " + str(group.get("name") or "Exercise"),
                               "number": str(group.get("number") or ""),
                               "timeslots": group.get("timeslots") or []}
                              for group in unit.get("groups", []) if isinstance(group, dict)]
                    meetings.extend(normalize_meetings(groups))
                    status, source = "ready", "local-dump"
                    # The export currently omits almost all Course.timeslots.
                    # Fetch only missing schedules, in the background; persist
                    # them separately and reuse them offline across restarts.
                    if any(not c.get("timeslots") for c in data) and unit.get("semkez"):
                        url = "https://www.vvz.ethz.ch/Vorlesungsverzeichnis/lerneinheit.view?" + urlencode({
                            "lerneinheitId": unit_id, "semkez": unit["semkez"], "ansicht": "ALLE", "lang": "en"})
                        official, status, source = self.server.vvz.scheduled(url)
                        if official is not None:
                            meetings.extend(normalize_meetings(official))
                    unique = {(m['day'], m['start'], m['end'], m['building'], m['floor'], m['room'],
                               m['date'], m['biweekly'], re.sub(r'\s+', '', m['courseNumber'])): m for m in meetings}
                    return self.respond(200, {"status": "ready", "groupStatus": status,
                                              "meetings": list(unique.values()), "source": "official-vvz" if source in ("cached", "live") else "local-dump",
                                              "scheduleStatus": status,
                                              "error": source if status == "failed" else None})
                data, status, source = self.server.vvz.scheduled(f"{CATALOG_BASE}/api/v1/course/get/{unit_id}")
                # Groups (e.g. exercise sections) live on the LearningUnit model,
                # not always in Course.timeslots. The second request is queued,
                # never made immediately if a minute has not elapsed.
                unit, group_status, _ = self.server.vvz.scheduled(f"{CATALOG_BASE}/api/v1/unit/{unit_id}/get")
                meetings = normalize_meetings(data) if status == "ready" else []
                if group_status == "ready" and isinstance(unit, dict):
                    groups = []
                    for group in unit.get("groups", []):
                        if isinstance(group, dict):
                            groups.append({"title": "Group: " + str(group.get("name") or "Exercise"),
                                           "number": str(group.get("number") or ""),
                                           "timeslots": group.get("timeslots") or []})
                    meetings.extend(normalize_meetings(groups))
                return self.respond(200, {"status": status, "groupStatus": group_status,
                                          "meetings": meetings, "source": source})
            except (RuntimeError, ValueError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path == "/" or path in ("/index.html", "/app.js", "/study-rules.js", "/styles.css", "/manifest.webmanifest", "/icon.svg"):
            filename = "index.html" if path == "/" else path[1:]
            fp = WEB / filename
            if not fp.exists():
                return self.respond(404, {"error": "not found"})
            types = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml"}
            content = fp.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", types.get(fp.suffix, "text/plain"))
            self.headers_common()
            self.send_header("Content-Length", str(len(content)))
            try:
                self.end_headers()
                return self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
                return
        return self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if not self.allowed_host():
            return self.respond(403, {"error": "Local access only"})
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://localhost:{self.server.server_port}",
                                     f"http://127.0.0.1:{self.server.server_port}",
                                     f"http://127.0.0.2:{self.server.server_port}"):
            return self.respond(403, {"error": "Cross-origin writes are blocked"})
        path = urlsplit(self.path).path
        if path == "/api/vvz/dump/check":
            return self.respond(200, self.server.vvz_dump.check(force=True))
        try:
            body = self.get_json()
            if path == "/api/state":
                try:
                    return self.respond(200, self.server.store.save(body))
                except RuntimeError as exc:
                    return self.respond(409, {"error": str(exc)})
            if path == "/api/grades":
                if not isinstance(body, dict) or not isinstance(body.get("salt"), str) or not isinstance(body.get("iv"), str) or not isinstance(body.get("ciphertext"), str):
                    raise ValueError("Expected encrypted grade payload")
                self.server.store._atomic(self.server.store.folder / "grades.enc", body)
                return self.respond(200, {"ok": True})
            if path == "/api/storage":
                mode = body.get("mode")
                if mode == "move":
                    folder = self.server.store.move(body.get("folder", ""))
                elif mode == "open":
                    folder = self.server.store.open_folder(body.get("folder", ""))
                else:
                    raise ValueError("Select move or open")
                return self.respond(200, {"folder": folder, "state": self.server.store.get()})
            if path == "/api/import":
                body = migrate_state(body)
                if not valid_state(body):
                    raise ValueError("Invalid imported data")
                old = self.server.store.get()
                body["revision"] = old["revision"]
                return self.respond(200, self.server.store.save(body))
            return self.respond(404, {"error": "Not found"})
        except RuntimeError as exc:
            return self.respond(409, {"error": str(exc)})
        except (ValueError, KeyError, json.JSONDecodeError, OSError, TypeError) as exc:
            return self.respond(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="MasterPlan study planner")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MASTERPLAN_PORT", "8765")))
    parser.add_argument("--host", default=os.environ.get("MASTERPLAN_HOST", "127.0.0.2"),
                        choices=("127.0.0.1", "127.0.0.2"), help="Local loopback address")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
        bound_host = args.host
    except OSError:
        if args.host != "127.0.0.2":
            raise
        # Some Windows/macOS installations do not assign other loopback aliases.
        bound_host = "127.0.0.1"
        server = ThreadingHTTPServer((bound_host, args.port), Handler)
        print("127.0.0.2 unavailable on this OS; using 127.0.0.1 instead.", flush=True)
    server.store = Store()
    # The catalogue lives OUTSIDE the personal sync folder, so it can be
    # re-downloaded and is never backed up with private plans or grades.
    cache_root = Path(os.environ.get("MASTERPLAN_CACHE_DIR", str(BASE / ".cache" / "vvz"))).expanduser().resolve()
    server.vvz = VvzCache(cache_root)
    server.catalog = LocalCatalog(cache_root / "database.sqlite", DEGREES, CATEGORY_PATHS,
                                  ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS)
    server.vvz_dump = VvzDump(cache_root, server.vvz, server.catalog)
    server.vvz_dump.check()  # async; never delays opening the local browser
    url = f"http://{bound_host}:{args.port}/"
    print(f"MasterPlan: {url}\nData: {server.store.folder}\nCtrl+C to stop", flush=True)
    if not args.no_browser:
        import webbrowser
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
