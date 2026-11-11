"""Historical references, bilingual course metadata and repeated weekly calendar meetings."""
import os
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from browser_semester_flow import Handler,Store,LocalCatalog,VvzCache,VvzDump,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS,initial_state,make_db

def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);db=root/'catalog.sqlite';make_db(db)
        with sqlite3.connect(db) as c:
            for name in ['abstract','abstract_english','objective','objective_english','content','content_english','literature','literature_english']:c.execute(f'ALTER TABLE learningunit ADD COLUMN {name} TEXT')
            c.execute("UPDATE learningunit SET abstract='Deutsche Beschreibung <script>window.injected=1</script>',abstract_english='English course description',objective='Deutsche Lernziele',objective_english='English learning objectives',content='Nur deutscher Inhalt' WHERE id=111")
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(root/'personal');http.catalog=LocalCatalog(db,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS);http.vvz=VvzCache(root/'cache');http.vvz_dump=VvzDump(root/'cache',http.vvz,http.catalog)
        s=initial_state();s['language']='de';s['actualPlan']['courses']=[dict(id='history',number='401-0000-00L',title='Introduction to Computational Physics',role='elective',ects=6,status='planned',semester='2027W',unitId=111,sourceSemester='2026W',offerings={'2026W':111},proxy=True,events=[]),dict(id='other',number='OTHER',title='Other semester module',role='extra',ects=0,status='planned',semester='2026W',events=[])]
        http.store.save(s);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(10000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));fetches=[];page.on('request',lambda r:fetches.append(r.url) if '/api/vvz/unit/' in r.url else None)
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');page.locator('[data-nav="semesters"]').click()
                assert page.locator('[data-warning="historical"]').count()>0;assert page.locator('[data-warning="season"]').count()==0
                page.locator('[data-action="reassign-course"][data-id="history"]').click();page.locator('#reassign-form [name="semester"]').select_option('2027S');page.locator('[data-action="apply-reassignment"]').click()
                page.wait_for_function("async()=>((await(await fetch('/api/state')).json()).actualPlan.courses[0].semester==='2027S')");assert page.locator('[data-warning="season"]').count()>0
                page.locator('[data-drag-course="history"] [data-action="course-details"]').click();page.wait_for_selector('.course-detail-text');assert 'Deutsche Lernziele' in page.locator('#app').inner_text();assert '<script>' in page.locator('#app').inner_text();assert page.locator('#app script').count()==0
                page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='en'");assert 'English learning objectives' in page.locator('#app').inner_text();assert 'Nur deutscher Inhalt' in page.locator('#app').inner_text();assert len(fetches)==1
                page.locator('[data-action="close-details"]').click();page.locator('[data-nav="schedule"]').click();page.locator('#schedule-sem').select_option('2027S')
                assert page.locator('#schedule-modules [data-schedule-course]').count()==1
                module=page.locator('[data-schedule-course="history"]');module.click();page.locator('.daycell[data-day="0"][data-start="08:00"]').click()
                form=page.locator('#event-form');assert form.locator('[name="course"]').input_value()=='history';assert form.locator('[name="start"]').input_value()=='08:00';form.locator('[name="end"]').fill('09:30');page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='de'");assert form.locator('[name="end"]').input_value()=='09:30';form.locator('button[type="submit"]').click()
                page.wait_for_function("async()=>((await(await fetch('/api/state')).json()).actualPlan.courses[0].events.length===1)")
                page.locator('[data-schedule-course="history"]').drag_to(page.locator('.daycell[data-day="2"][data-start="10:00"]'))
                assert form.locator('[name="day"]').input_value()=='2';assert form.locator('[name="start"]').input_value()=='10:00';form.locator('button[type="submit"]').click()
                page.wait_for_function("async()=>((await(await fetch('/api/state')).json()).actualPlan.courses[0].events.length===2)")
                page.reload();page.wait_for_selector('.metric');page.locator('[data-nav="schedule"]').click();page.locator('#schedule-sem').select_option('2027S');page.wait_for_selector('.event');assert page.locator('.event').count()==2
                assert not errors,errors;print('HISTORY/DETAILS/CALENDAR PASSED: reference and season warnings, persisted move, escaped bilingual metadata, cache/fallback, semester-scoped palette, click and native drag to create two meetings');b.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
