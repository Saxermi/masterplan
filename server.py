"""MasterPlan: local-only HTTP application with atomic portable storage and VVZ proxy."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
DEFAULT_DATA = Path(os.environ.get("MASTERPLAN_DATA_DIR", str(BASE / "user-data"))).expanduser().resolve()
MAX_BODY = 2 * 1024 * 1024
CATALOG_BASE = "https://vvzapi.ch"
DEGREES = {
    "cse": "computational science and engineering",
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


def build_catalog_query(query, programme, category):
    """Return a VVZAPI offered-section query, rejecting unsupported eligibility claims."""
    if programme not in DEGREES:
        raise ValueError("Unknown programme")
    if category not in ("", "core", "elective", "eligible-core"):
        raise ValueError("Unknown course category")
    clean = query.strip()[:120].replace('"', '')
    if category == "eligible-core":
        if programme == "eligible-core-all":
            # A module can appear in multiple programmes: VVZ compact search
            # groups by course number and naturally deduplicates these results.
            distinct_paths = sorted({DEGREES[p] for p in ELIGIBLE_CORE_PROGRAMMES})
            clauses = [f'(o:"{p}" o:"core courses")' for p in distinct_paths]
            course_query = "(" + " OR ".join(clauses) + ")"
        elif programme in ELIGIBLE_CORE_PROGRAMMES:
            course_query = f'o:"{DEGREES[programme]}" o:"core courses"'
        else:
            raise ValueError("Select an eligible MSc programme for CSE core-course electives")
        return " ".join([course_query, f'title:"{clean}"' if clean else ""]).strip()
    if programme == "eligible-core-all":
        raise ValueError("Choose the CSE-elective core-course category")
    clauses = []
    if DEGREES[programme]:
        clauses.append(f'o:"{DEGREES[programme]}"')
    if category in ("core", "elective"):
        clauses.append(f'o:"{"core courses" if category == "core" else "electives"}"')
    if clean:
        clauses.append(f'title:"{clean}"')
    if not clauses:
        raise ValueError("Provide a search term or select a programme")
    return " ".join(clauses)


def initial_state():
    return {
        "schema": 1,
        "revision": 0,
        "language": "de",
        "theme": "light",
        "activePlan": "physics",
        "selectedSpecialisations": ["Physics", "Fluid Dynamics"],
        "history": [],
        "plans": [
            {"id": "physics", "name": "Physics Specialisation", "specialisation": "Physics", "semesters": ["2026W", "2027S", "2027W", "2028S"], "lockedSemesters": [], "courses": [], "notes": ""},
            {"id": "fluids", "name": "Fluid Dynamics Specialisation", "specialisation": "Fluid Dynamics", "semesters": ["2026W", "2027S", "2027W", "2028S"], "lockedSemesters": [], "courses": [], "notes": ""},
        ],
    }


def valid_state(x):
    if not isinstance(x, dict) or x.get("schema") != 1 or not isinstance(x.get("plans"), list):
        return False
    if any("grade" in str(k).lower() or "notevalue" in str(k).lower() for k in x) or len(x["plans"]) > 100 or not isinstance(x.get("history"), list):
        return False
    if x.get("language") not in ("de", "en") or x.get("theme") not in ("light", "dark"):
        return False
    ids = set()
    for plan in x["plans"]:
        if not isinstance(plan, dict) or not isinstance(plan.get("id"), str) or len(plan.get("name", "")) > 150:
            return False
        if plan["id"] in ids or not isinstance(plan.get("courses"), list) or not isinstance(plan.get("semesters"), list):
            return False
        if any("grade" in str(k).lower() for k in plan):
            return False
        ids.add(plan["id"])
        if len(plan["courses"]) > 300 or len(plan["semesters"]) > 30:
            return False
        for course in plan["courses"]:
            if not isinstance(course, dict) or not isinstance(course.get("id"), str) or not isinstance(course.get("semester"), str):
                return False
            if any("grade" in str(k).lower() for k in course):
                return False
            if course.get("role", "extra") not in ("core", "specialisation", "elective", "case", "project", "sip", "thesis", "extra", "requirement"):
                return False
    return True


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
            return json.loads((self.folder / "masterplan.json").read_text(encoding="utf-8"))

    def save(self, incoming):
        with self.lock:
            old = self.get()
            if not valid_state(incoming):
                raise ValueError("Invalid MasterPlan data format")
            if incoming.get("revision") != old["revision"]:
                raise RuntimeError("Revision conflict: reload before saving")
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
            if not state_file.is_file() or not valid_state(json.loads(state_file.read_text(encoding="utf-8"))):
                raise ValueError("No valid MasterPlan data in selected folder")
            self.folder = target
            return str(target)


class VvzCache:
    """Global 60-second upstream rate limit, cached by URL, shared across tabs."""

    def __init__(self, folder):
        self.lock = threading.RLock()
        self.last_request = 0.0
        self.cache = {}
        self.folder = Path(folder)

    def get(self, url):
        with self.lock:
            now = time.monotonic()
            entry = self.cache.get(url)
            if entry and now - entry[0] < 1800:
                return entry[1], "cached"
            if now - self.last_request < 60:
                if entry:
                    return entry[1], "stale"
                raise RuntimeError(f"VVZ rate limit: retry in {int(60 - (now - self.last_request)) + 1}s")
            self.last_request = now  # reserve before request, including failed requests
            request = Request(url, headers={"User-Agent": "MasterPlan-study-planner/0.1 (+https://github.com/Saxermi/masterplan)", "Accept": "application/json"})
            try:
                with urlopen(request, timeout=12) as response:
                    if int(response.headers.get("Content-Length", "0")) > 4_000_000:
                        raise ValueError("Upstream response too large")
                    raw = response.read(4_000_001)
                    if len(raw) > 4_000_000:
                        raise ValueError("Upstream response too large")
                    result = json.loads(raw)
                    if not isinstance(result, (dict, list)):
                        raise ValueError("Unexpected upstream response")
                    self.cache[url] = (now, result)
                    return result, "live"
            except (HTTPError, URLError, ValueError, TimeoutError) as exc:
                if entry:
                    return entry[1], "stale"
                raise RuntimeError(f"VVZ unavailable: {exc}") from exc


def sem_label(code):
    return ("FS " if code.endswith("S") else "HS ") + code[:4]


def select_offering(semesters, wanted):
    """Prefer exact semester; otherwise use closest previous same-season offering."""
    if wanted in semesters:
        return {"unit_id": semesters[wanted], "source_semester": wanted, "proxy": False}
    earlier = [s for s in semesters if re.fullmatch(r"\d{4}[SW]", s) and s.endswith(wanted[-1]) and s < wanted]
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
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        host = self.headers.get("Host", "").split(":")[0].lower()
        return host in ("localhost", "127.0.0.1", "[::1]")

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
        if path == "/api/vvz/search":
            try:
                query = params.get("q", [""])[0].strip()[:120]
                programme = params.get("programme", ["cse"])[0]
                category = params.get("category", [""])[0]
                semester = params.get("semester", [""])[0]
                vvz_query = build_catalog_query(query, programme, category)
                if re.fullmatch(r"\d{4}[SW]", semester):
                    # Keep all offerings, because a previous same-season one might be used as proxy.
                    pass
                limit = min(60, max(1, int(params.get("limit", ["40"])[0])))
                offset = max(0, min(10000, int(params.get("offset", ["0"])[0])))
                url = CATALOG_BASE + "/api/v0/search/compact?" + urlencode({"q": vvz_query, "offset": offset, "limit": limit, "order_by": "title", "order": "asc"})
                data, source = self.server.vvz.get(url)
                if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                    raise ValueError("Invalid VVZ search result")
                results = []
                for row in data["results"]:
                    if not isinstance(row, dict):
                        continue
                    item = {k: row.get(k) for k in ("number", "title", "title_english", "credits", "semesters", "levels", "language")}
                    if re.fullmatch(r"\d{4}[SW]", semester):
                        item["offering"] = select_offering(row.get("semesters") or {}, semester)
                    results.append(item)
                return self.respond(200, {"results": results, "total": data.get("total"), "source": source, "query": vvz_query, "eligibleCoreElective": category == "eligible-core"})
            except (RuntimeError, ValueError, TypeError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path.startswith("/api/vvz/unit/"):
            try:
                unit_id = int(path.rsplit("/", 1)[-1])
                if not (1 <= unit_id <= 1_000_000_000):
                    raise ValueError("Invalid unit id")
                data, source = self.server.vvz.get(f"{CATALOG_BASE}/api/v1/unit/{unit_id}/get")
                return self.respond(200, {"unit": data, "source": source})
            except (RuntimeError, ValueError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path.startswith("/api/vvz/times/"):
            try:
                unit_id = int(path.rsplit("/", 1)[-1])
                if not 1 <= unit_id <= 1_000_000_000:
                    raise ValueError("Invalid unit id")
                data, source = self.server.vvz.get(f"{CATALOG_BASE}/api/v1/course/get/{unit_id}")
                return self.respond(200, {"courses": data, "source": source})
            except (RuntimeError, ValueError) as exc:
                return self.respond(503, {"error": str(exc)})
        if path == "/" or path in ("/index.html", "/app.js", "/styles.css", "/manifest.webmanifest", "/icon.svg"):
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
            self.end_headers()
            return self.wfile.write(content)
        return self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if not self.allowed_host():
            return self.respond(403, {"error": "Local access only"})
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"):
            return self.respond(403, {"error": "Cross-origin writes are blocked"})
        path = urlsplit(self.path).path
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
                if not valid_state(body):
                    raise ValueError("Invalid imported data")
                old = self.server.store.get()
                body["revision"] = old["revision"]
                return self.respond(200, self.server.store.save(body))
            return self.respond(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError, OSError, TypeError) as exc:
            return self.respond(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="MasterPlan study planner")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MASTERPLAN_PORT", "8765")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.store = Store()
    server.vvz = VvzCache(server.store.folder)
    url = f"http://127.0.0.1:{args.port}/"
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
