"""End-to-end HS26 test against a real VVZ dump, with public ETH schedule fixtures.

python3 tests/browser_hs26.py --database /path/to/database.sqlite [--export example.json]
Uses an isolated temporary personal folder, the real local HTTP API and browser.
No upstream requests: official public schedule responses are seeded from fixtures.
"""
import argparse
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import Handler, Store, VvzCache, DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS
from vvz_dump import LocalCatalog, VvzDump
from vvz_schedule import parse_official_courses


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--database', required=True)
    args.add_argument('--export')
    args.add_argument('--screenshot')
    args = args.parse_args()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.store = Store(root / 'personal')
        server.vvz = VvzCache(root / 'cache')
        server.catalog = LocalCatalog(args.database, DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS)
        server.vvz_dump = VvzDump(root / 'cache', server.vvz, server.catalog)
        for uid, name in [(204828, 'ai'), (204354, 'numerical')]:
            url = 'https://www.vvz.ethz.ch/Vorlesungsverzeichnis/lerneinheit.view?' + urlencode({
                'lerneinheitId': uid, 'semkez': '2026W', 'ansicht': 'ALLE', 'lang': 'en'})
            courses = parse_official_courses((ROOT / f'tests/fixtures/{name}-hs26.html').read_text())
            Store._atomic(server.vvz._schedule_file(url), {'checked': time.time(), 'courses': courses})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'), args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                errors = []
                page.on('pageerror', lambda err: errors.append(str(err)))
                page.set_default_timeout(10000)
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.wait_for_selector('.metric')
                for programme, category, query, number in [
                    ('cse', 'core', 'AI Science and Engineering', '401-4656-21L'),
                    ('cse-bsc', 'requirement', 'Numerical Methods for Computational Science and Engineering', '401-2673-00L')]:
                    page.locator('[data-nav="catalog"]').click()
                    page.locator('[name="programme"]').select_option(programme)
                    page.locator('[name="category"]').select_option(category)
                    page.locator('[name="semester"]').select_option('2026W')
                    page.locator('[name="q"]').fill(query)
                    page.locator('#search-form button[type="submit"]').click()
                    page.locator(f'[data-action="shortlist-result"][data-number="{number}"]').click()
                    page.wait_for_function("async(n)=>(await (await fetch('/api/state')).json()).interests.some(c=>c.number===n)", arg=number)
                    page.locator('[data-nav="semesters"]').click()
                    interest = page.evaluate("async(n)=>(await (await fetch('/api/state')).json()).interests.find(c=>c.number===n).id", number)
                    page.locator(f'#assign-course-form input[name="interest"][value="{interest}"]').check()
                    page.locator('#assign-course-form [name="semester"]').select_option('2026W')
                    page.locator('[data-action="assign-interest"]').click()
                    page.wait_for_function("async(n)=>(await (await fetch('/api/state')).json()).actualPlan.courses.some(c=>c.number===n)", arg=number)
                page.locator('[data-nav="schedule"]').click()
                page.wait_for_function('()=>document.querySelectorAll(".meeting-options").length===2')
                for title, days in [('AI in the Sciences and Engineering', ['Mo', 'Do']), ('Numerical Methods for CSE', ['Di', 'Fr'])]:
                    unit = page.locator('.meeting-unit').filter(has=page.locator('.course-name', has_text=title))
                    for day in days:
                        option = unit.locator('.meeting-option').filter(has_text='· '+day+' ').first
                        option.locator('input').check()
                    unit.locator('[data-action="apply-vvz-slots"]').click()
                    page.wait_for_function("async(title)=>(await (await fetch('/api/state')).json()).actualPlan.courses.find(c=>c.title===title).events.length===2", arg=title)
                page.reload()
                page.wait_for_selector('.metric')
                page.locator('[data-nav="schedule"]').click()
                page.wait_for_selector('.event')
                assert page.locator('.event').count() == 4
                saved = server.store.get()
                ai, numerical = saved['actualPlan']['courses']
                assert (ai['role'], ai['ects'], numerical['role'], numerical['ects']) == ('core', 6, 'requirement', 9)
                assert all(c['semester'] == '2026W' and not c['proxy'] for c in (ai, numerical))
                assert not errors, errors
                if args.export:
                    saved['actualPlan']['name'] = 'HS26 Test: AI Core + Numerical Methods Auflage'
                    saved['actualPlan']['notes'] = ('Public ETH HS26 test case, verified 2026-11-08. Numerical Methods: first lecture week in HG G 5, subsequent weeks HG G 19.1. Exercise group selected: HG F 26.5. Admission recognition depends on the personal admission letter.')
                    Path(args.export).parent.mkdir(parents=True, exist_ok=True)
                    Path(args.export).write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
                if args.screenshot:
                    Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=args.screenshot, full_page=True)
                print('HS26 E2E PASSED: real dump search, shortlist, assign, official slots, roles, ECTS, persistence after reload; 4 events')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    main()
