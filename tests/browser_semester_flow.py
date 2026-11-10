import os
import shutil
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from browser_allocations import ROOT
from server import Handler, Store, LocalCatalog, VvzCache, VvzDump, DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS, initial_state
from test_vvz_dump import make_db

def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);db=root/'catalog.sqlite';make_db(db)
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(root/'personal')
        http.catalog=LocalCatalog(db,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS)
        http.vvz=VvzCache(root/'cache');http.vvz_dump=VvzDump(root/'cache',http.vvz,http.catalog)
        state=http.store.get();state['language']='en';state['interests']=[dict(id='interest',number='401-0000-00L',title='Synthetic autumn course',ects=6,suggestedRole='core',unitId=111,sourceSemester='2026W',offerings={'2026W':111})];http.store.save(state)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page();page.set_default_timeout(8000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric')
                page.locator('[data-nav="plans"]').click();page.locator('[data-action="edit-scenario"][data-id="physics"]').click();page.wait_for_selector('#scenario-specialisation')
                assert http.store.get()['activePlan']=='physics'
                page.locator('[data-nav="schedule"]').click();page.locator('[data-action="focus-schedule-assign"]').click()
                form=page.locator('#assign-course-form');assert form.locator('[name="plan"]').input_value()=='physics'
                form.locator('input[name="interest"]').check();form.locator('[name="semester"]').select_option('2026W');form.locator('[data-action="assign-interest"]').click()
                page.wait_for_selector('#event-form');assert 'lerneinheitId=111' in page.locator('#manual-vvz-link a').first.get_attribute('href')
                ev=page.locator('#event-form');ev.locator('[name="start"]').fill('08:15');ev.locator('[name="end"]').fill('10:00');ev.locator('button[type="submit"]').click();page.wait_for_selector('.event')
                page.locator('[data-nav="semesters"]').click();page.locator('[data-action="reassign-course"][data-plan-id="physics"]').click()
                form=page.locator('#reassign-form');form.locator('[name="plan"]').select_option('actual');form.locator('[name="role"]').select_option('elective');form.locator('[data-action="apply-reassignment"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses.length===1)")
                assert http.store.get()['actualPlan']['courses'][0]['role']=='elective';assert http.store.get()['plans'][0]['courses']==[]
                page.locator('[data-action="reassign-course"][data-plan-id="actual"]').click();page.locator('#reassign-form [name="semester"]').select_option('2027S');page.locator('[data-action="apply-reassignment"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses[0].semester==='2027S')");assert page.locator('[data-warning="season"]').count()>0
                page.locator('[data-action="remove-semester"][data-plan-id="actual"][data-sem="2028S"]').click()
                page.wait_for_function("async()=>!(await (await fetch('/api/state')).json()).actualPlan.semesters.includes('2028S')")
                page.once('dialog',lambda dialog:dialog.dismiss());page.locator('[data-action="remove-semester"][data-plan-id="actual"][data-sem="2027S"]').click();assert len(http.store.get()['actualPlan']['courses'])==1
                page.once('dialog',lambda dialog:dialog.accept());page.locator('[data-action="remove-semester"][data-plan-id="actual"][data-sem="2027S"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses.length===0)");assert len(http.store.get()['interests'])==1
                page.locator('[data-nav="catalog"]').click();assert page.locator('#search-form [name="semester"] option[value="recent"]').count()==0
                page.locator('#search-form [name="semester"]').select_option('2026W');page.locator('#search-form [name="semester2"]').select_option('2026S');page.locator('#search-form button[type="submit"]').click();page.wait_for_selector('[data-action="shortlist-result"]')
                page.locator('[data-action="shortlist-assign"]').first.click();page.wait_for_selector('#assign-course-form');assert page.locator('#assign-course-form [name="semester"]').input_value()=='2026W'
                assert not errors,errors
                print('SEMESTER FLOW PASSED: empty scenario, inline assignment, historical-term warnings, VVZ/manual time, editable plan/category, semester removal and two-term search')
                b.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
