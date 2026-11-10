"""Real Chromium batch-selection and native drag-and-drop regression. Synthetic local data only."""
import os
import shutil
import tempfile
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import Mock
from playwright.sync_api import sync_playwright
from browser_allocations import ROOT,course
from server import Handler,Store,initial_state

def main():
    with tempfile.TemporaryDirectory() as d:
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d);http.vvz_dump=Mock();http.vvz_dump.status.return_value={'available':False,'phase':'missing'}
        s=initial_state();s['language']='en';s['actualPlan']['courses']=[course('core',6,locked=True,number='LOCK',title='Locked assigned')]
        s['interests']=[dict(id=k,number=k.upper(),title=title,ects=6,suggestedRole=role,offerings={}) for k,title,role in [('a','Alpha','core'),('b','Beta','elective'),('lock','Locked assigned','core'),('c','Gamma','extra')]]
        http.store.save(s);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1800,'height':1200});page.set_default_timeout(8000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');page.locator('[data-nav="semesters"]').click()
                form=page.locator('#assign-course-form');assert form.locator('input[name="interest"]').count()==3
                form.locator('[name="filter"]').fill('Alpha');assert form.locator('input[name="interest"]').count()==1
                form.locator('[data-action="select-visible"]').click();form.locator('[name="filter"]').fill('');form.locator('input[value="b"]').check()
                assert '2 selected' in form.locator('#assignment-count').inner_text();form.locator('[data-action="assign-interest"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses.length===3)")
                assert page.locator('#assignment-choices input').count()==1
                saved=http.store.get();a=next(c for c in saved['actualPlan']['courses'] if c['number']=='A');bb=next(c for c in saved['actualPlan']['courses'] if c['number']=='B')
                assert (a['role'],bb['role'])==('core','elective')
                source=page.locator(f'[data-drag-plan="actual"][data-drag-course="{a["id"]}"]');target=page.locator('[data-drop-plan="actual"][data-drop-sem="2027S"]')
                source.drag_to(target)
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses.find(c=>c.number==='A').semester==='2027S')")
                # Lock destination and verify native dragging cannot change the source record.
                page.locator('[data-action="lock-semester"][data-plan-id="actual"][data-sem="2027S"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.lockedSemesters.includes('2027S'))")
                page.locator(f'[data-drag-plan="actual"][data-drag-course="{bb["id"]}"]').drag_to(target)
                page.wait_for_selector('#toast.show');assert 'locked' in page.locator('#toast').inner_text()
                assert next(c for c in http.store.get()['actualPlan']['courses'] if c['number']=='B')['semester']=='2026W'
                locked=page.locator('[data-drag-plan="actual"]',has_text='Locked assigned');assert locked.get_attribute('draggable')=='false'
                # A separate hypothetical plan still has its own unassigned list.
                page.locator('#assign-course-form [name="plan"]').select_option('physics');assert page.locator('#assignment-choices input').count()==4
                page.reload();page.wait_for_selector('.metric');page.locator('[data-nav="semesters"]').click();assert page.locator('#assignment-choices input').count()==1
                assert not errors,errors;print('BULK BROWSER PASSED: filtered multi-selection, one-save batch, assigned/locked hiding, native drag/drop, locked destination, per-plan choices and persistence')
                b.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
