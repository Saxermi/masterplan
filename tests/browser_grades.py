"""Encrypted partial grades, bonuses, scenarios and actual-result inheritance over real HTTP."""
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from browser_allocations import ROOT,baseline
from server import Handler,Store


def main():
    with tempfile.TemporaryDirectory() as d:
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d);s=baseline();http.store.save(s)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(10000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');page.locator('[data-nav="grades"]').click()
                page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-vault-password');page.locator('#grades-unlock-form button').click();page.wait_for_selector('[data-action="grade-add"]')
                page.locator('[data-action="grade-add"]').click();page.locator('[data-grade-link]').select_option(s['actualPlan']['courses'][0]['id'])
                page.locator('[data-grade-part="0"][data-grade-input="name"]').fill('PRIVATE-MIDTERM-XYZ')
                page.locator('[data-grade-part="0"][data-grade-input="value"]').fill('5');page.locator('[data-grade-part="1"][data-grade-input="estimate"]').fill('4');page.locator('[data-grade-input="bonus"]').fill('0.25')
                assert page.locator('[data-projected-grade]').inner_text()=='4.45';assert page.locator('[data-required-grade]').inner_text()=='3.44'
                page.locator('#grade-entry-form button[type="submit"]').click();page.locator('[data-action="grade-save"]').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('encrypted and saved')")
                encrypted=Path(d,'grades.enc').read_text();assert 'PRIVATE-MIDTERM-XYZ' not in encrypted;assert 'entries' not in encrypted
                raw=Path(d,'masterplan.json').read_text();assert 'PRIVATE-MIDTERM-XYZ' not in raw and 'simulations' not in raw
                page.locator('[data-nav="simulation"]').click();page.locator('#simulation-create-form [name="name"]').fill('Optimistic');page.locator('#simulation-create-form [name="useActual"]').select_option('yes');page.locator('#simulation-create-form button').click();page.wait_for_selector('#simulation-plan')
                assert page.locator('#simulation-plan').input_value()=='actual';assert 'Actual results inherited' in page.locator('#app').inner_text()
                key='number:'+s['actualPlan']['courses'][0]['number']
                page.locator(f'[data-action="simulation-edit"][data-key="{key}"]').click()
                assert page.locator('[data-grade-part="0"][data-grade-input="value"]').input_value()=='5';assert page.locator('[data-grade-part="0"][data-grade-input="value"]').get_attribute('readonly') is not None
                assert page.locator('[data-grade-part="0"][data-grade-input="weight"]').get_attribute('readonly') is not None
                page.locator('[data-grade-part="1"][data-grade-input="estimate"]').fill('5');page.locator('#grade-entry-form button[type="submit"]').click()
                for c in s['actualPlan']['courses']:
                    if c['id']==s['actualPlan']['courses'][0]['id'] or c['role'] not in ['core','specialisation','elective','thesis'] or c.get('subtype')=='seminar':continue
                    key='number:'+c['number'];page.locator(f'[data-action="simulation-edit"][data-key="{key}"]').click();page.locator('[data-grade-part="0"][data-grade-input="estimate"]').fill('5');page.locator('#grade-entry-form button[type="submit"]').click()
                assert page.locator('#private-final .metric').inner_text()=='5.04'
                original=page.locator('#simulation-select').input_value();page.locator('[data-action="simulation-duplicate"]').click();assert page.locator('#simulation-select option').count()==2
                page.locator(f'[data-action="simulation-edit"][data-key="number:{s["actualPlan"]["courses"][1]["number"]}"]').click();page.locator('[data-grade-part="0"][data-grade-input="estimate"]').fill('4');page.locator('#grade-entry-form button[type="submit"]').click();assert page.locator('#private-final .metric').inner_text()=='4.89'
                page.locator('#simulation-select').select_option(original);assert page.locator('#private-final .metric').inner_text()=='5.04'
                page.locator('[data-action="grade-save"]').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('encrypted and saved')")
                page.locator('[data-nav="dashboard"]').click();assert 'PRIVATE-MIDTERM-XYZ' not in page.locator('#app').inner_text();assert page.locator('[data-grade-input]').count()==0
                page.locator('[data-nav="simulation"]').click();page.locator('#grades-unlock-form [name="password"]').fill('incorrect-password');page.locator('#grades-unlock-form button').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('Wrong password')")
                page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-vault-password');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#simulation-select');page.locator('#simulation-select').select_option(original);assert page.locator('#private-final .metric').inner_text()=='5.04'
                page.locator('[data-nav="grades"]').click();page.locator('[data-action="grade-edit"]').click();page.locator('[data-grade-part="0"][data-grade-input="value"]').fill('4.5');page.locator('#grade-entry-form button[type="submit"]').click()
                page.locator('[data-nav="simulation"]').click();page.locator(f'[data-action="simulation-edit"][data-key="number:{s["actualPlan"]["courses"][0]["number"]}"]').click();assert page.locator('[data-grade-part="0"][data-grade-input="value"]').input_value()=='4.5'
                # A hypothetical study plan does not silently inherit actual marks.
                page.locator('[data-action="grade-draft-cancel"]').click();page.locator('#simulation-plan').select_option('physics');assert 'Actual results inherited' not in page.locator('#app').inner_text()
                assert not errors,errors;print('GRADES BROWSER PASSED: 20/80 components, 0.25 bonus, required exam grade, encrypted round-trip, scenario final grade/duplication, protected actual marks, live updates, privacy and wrong password');b.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
