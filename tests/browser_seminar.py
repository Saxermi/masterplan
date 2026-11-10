"""Bilingual category selection and persisted recognition of a four-credit Physics seminar."""
import os
import shutil
import tempfile
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from browser_allocations import ROOT,baseline
from server import Handler,Store

def main():
    with tempfile.TemporaryDirectory() as d:
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d)
        s=baseline();seminar=next(c for c in s['actualPlan']['courses'] if c.get('subtype')=='seminar');seminar.update(title='Seminar in Physics',ects=4);seminar.pop('subtype');s['language']='de';http.store.save(s)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page();page.set_default_timeout(8000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');page.locator('[data-nav="requirements"]').click()
                spec=page.locator('[data-requirement="spec"]').first;assert spec.get_attribute('data-potential')=='true';assert '4/4' in spec.inner_text();assert '1/1' in spec.inner_text()
                page.locator('[data-nav="semesters"]').click();page.locator(f'[data-action="reassign-course"][data-id="{seminar["id"]}"]').click()
                role=page.locator('#reassign-form [name="role"]');assert role.input_value()=='specialisation-seminar';assert role.locator('option:checked').inner_text()=='Spezialisierungsseminar'
                role.select_option('specialisation');page.locator('[data-action="apply-reassignment"]').click();page.wait_for_function("async(id)=>(await(await fetch('/api/state')).json()).actualPlan.courses.find(c=>c.id===id).subtype==='lecture'",arg=seminar['id'])
                page.locator(f'[data-action="reassign-course"][data-id="{seminar["id"]}"]').click();page.locator('#reassign-form [name="role"]').select_option('specialisation-seminar');page.locator('[data-action="apply-reassignment"]').click()
                page.wait_for_function("async(id)=>(await(await fetch('/api/state')).json()).actualPlan.courses.find(c=>c.id===id).subtype==='seminar'",arg=seminar['id'])
                page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='en'")
                page.locator(f'[data-action="reassign-course"][data-id="{seminar["id"]}"]').click();assert page.locator('#reassign-form [name="role"] option:checked').inner_text()=='Specialisation seminar'
                page.reload();page.wait_for_selector('.metric');page.locator('[data-nav="requirements"]').click();assert page.locator('[data-requirement="spec"]').first.get_attribute('data-potential')=='true'
                assert not errors,errors;print('SEMINAR BROWSER PASSED: 4-credit Physics seminar, legacy recognition, separate DE/EN category, reclassification and persistence');b.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
