"""Simulation defaults, preserved local grades and explicit scenario saving over real HTTP."""
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import Mock
from playwright.sync_api import sync_playwright
from browser_allocations import baseline,Handler,Store


def main():
    with tempfile.TemporaryDirectory() as d:
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d);http.vvz_dump=Mock();http.vvz_dump.status.return_value={'available':False,'phase':'missing'}
        state=baseline();courses=state['actualPlan']['courses'];a,b,c,mean_only,unmatched=courses[:5]
        a['title']='AI Science and Engineering (demo)';b['title']='Numerical Methods (demo)';c['title']='Physics statistics missing (demo)';mean_only['title']='Mean known, deviation missing (demo)';unmatched['title']='No imported record (demo)'
        http.store.save(state);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=browser.new_page(viewport={'width':1600,'height':1200},locale='en-GB');page.set_default_timeout(10000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                def shot(name,selector):
                    if os.getenv('SCREENSHOT_DIR'):
                        folder=Path(os.environ['SCREENSHOT_DIR']);folder.mkdir(parents=True,exist_ok=True);page.locator(selector).screenshot(path=str(folder/name),type='jpeg',quality=85)
                def nav(where):page.locator(f'[data-nav="{where}"]').click()
                def unlock():page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-defaults-vault');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#exchange-form')
                def row(course):return page.locator(f'[data-simulation-row="number:{course["number"]}"]')
                def grade(course):return row(course).locator('[data-simulation-grade]').inner_text()
                def quick(course,value):
                    form=row(course).locator('form');form.locator('[name="grade"]').fill(str(value));form.locator('button[type="submit"]').click()
                def fallback(value):
                    form=page.locator('#simulation-default-form');form.locator('[name="grade"]').fill(str(value));form.locator('button').click()
                def sigma(value):
                    form=page.locator('#statistics-adjust-form');form.locator('[name="factor"]').fill(str(value));form.locator('button[type="submit"]').click()
                def save():
                    page.get_by_role('button',name='Save scenarios',exact=True).click();page.wait_for_selector('[data-scenario-save-state="saved"]')
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');nav('simulation');unlock()
                stats=dict(schemaVersion=1,kind='masterplan-statistics',name='Sparse synthetic statistics',courses=[dict(number=a['number'],semester='2026W',mean=5,stddev=.5,passRate=85),dict(number=c['number'],semester='2026W',mean=None,stddev=None,passRate=75),dict(number=mean_only['number'],semester='2026W',mean=5,stddev=None)])
                page.locator('#exchange-form [name="json"]').fill(json.dumps(stats));page.locator('#exchange-form button').click();page.locator('[data-action="exchange-apply"]').click();form=page.locator('#statistics-scenario-form');form.locator('[name="name"]').fill('Planning at minus one sigma');form.locator('[name="factor"]').fill('-1');form.locator('[name="fallbackGrade"]').fill('4.5');form.locator('[name="useActual"]').select_option('no');form.locator('button[type="submit"]').click()
                assert page.locator('#private-final .metric').inner_text()=='4.50';assert grade(a)=='4.50' and grade(b)=='4.50' and grade(c)=='4.50';assert row(b).get_attribute('data-source')=='fallback'
                page.locator(f'[data-action="simulation-edit"][data-key="number:{a["number"]}"]').click();page.locator('#grade-entry-form button[type="submit"]').click();assert row(a).get_attribute('data-source')=='statistics'
                page.locator(f'[data-action="simulation-edit"][data-key="number:{a["number"]}"]').click();page.locator('[data-grade-input="targetGrade"]').fill('5');page.locator('#grade-entry-form button[type="submit"]').click();assert row(a).get_attribute('data-source')=='statistics'
                quick(b,5);page.locator(f'[data-action="simulation-edit"][data-key="number:{c["number"]}"]').click();page.locator('[data-grade-part="0"][data-grade-input="estimate"]').fill('5.25');page.locator('#grade-entry-form button[type="submit"]').click();quick(unmatched,5.5)
                sigma(1);assert grade(a)=='5.50';assert grade(b)=='5.00' and grade(c)=='5.25' and grade(unmatched)=='5.50';assert grade(mean_only)=='4.50';assert page.locator('#private-final .metric').inner_text()=='4.84'
                fallback(4.75);assert grade(b)=='5.00' and grade(c)=='5.25' and grade(unmatched)=='5.50' and grade(mean_only)=='4.75'
                # A local override is also protected when a valid imported mean exists.
                quick(a,4.8);sigma(-1);assert grade(a)=='4.80';row(a).locator('[data-action="simulation-reset-override"]').click();assert grade(a)=='4.50'
                fallback('');assert grade(mean_only)=='—';assert grade(c)=='5.25' and grade(unmatched)=='5.50';row(b).locator('[data-action="simulation-reset-override"]').click();assert grade(b)=='—'
                page.locator('#simulation-course-filter').select_option('unknown');assert page.locator('[data-simulation-row]:visible').count()>0;assert page.locator('[data-simulation-row]:visible').count()<15;page.locator('#simulation-course-filter').select_option('all')
                fallback(5);assert grade(b)=='5.00';page.locator('#simulation-course-search').fill('Numerical Methods');assert page.locator('[data-simulation-row]:visible').count()==1;page.locator('#simulation-course-search').fill('')
                # Unsaved inline text survives unrelated recomputation; Save includes it.
                row(b).locator('[name="grade"]').fill('5.1');sigma(1);assert row(b).locator('[name="grade"]').input_value()=='5.1';assert grade(b)=='5.00';assert page.locator('[data-scenario-save-state="dirty"]').count()==1
                save();assert grade(b)=='5.10';assert row(b).get_attribute('data-source')=='manual';assert page.locator('[data-scenario-save-state="saved"]').count()==1
                shot('40-simulation-fallback-settings.jpg','#simulation-defaults');page.locator('#simulation-course-search').fill('demo');shot('41-simulation-local-overrides.jpg','#simulation-courses');page.locator('#simulation-course-search').fill('')
                first_scene=page.locator('#simulation-select').input_value()
                # Saving multiple named scenarios also restores the selected one on reload.
                page.locator('#simulation-new summary').click();form=page.locator('#simulation-create-form');form.locator('[name="name"]').fill('Alternative fallback plan');form.locator('[name="fallbackGrade"]').fill('4.25');form.locator('[name="useActual"]').select_option('no');form.locator('button').click();assert page.locator('#private-final .metric').inner_text()=='4.25';save();second_scene=page.locator('#simulation-select').input_value()
                page.reload();page.wait_for_selector('.metric');nav('simulation');unlock();assert page.locator('#simulation-select').input_value()==second_scene;assert page.locator('#simulation-select option').count()==2;assert page.locator('#private-final .metric').inner_text()=='4.25'
                page.locator('#simulation-select').select_option(first_scene);assert grade(b)=='5.10' and grade(c)=='5.25' and grade(unmatched)=='5.50';assert page.locator('#simulation-default-form [name="grade"]').input_value()=='5'
                # A pending component edit survives sigma changes and is included by Save.
                page.locator(f'[data-action="simulation-edit"][data-key="number:{c["number"]}"]').click();page.locator('[data-grade-part="0"][data-grade-input="estimate"]').fill('5.4');sigma(-1);assert page.locator('[data-grade-part="0"][data-grade-input="estimate"]').input_value()=='5.4';save();assert grade(c)=='5.40'
                shot('42-scenarios-saved.jpg','.scenario-save-toolbar')
                # Missing-assumption filtering also catches an incomplete local override.
                page.locator(f'[data-action="simulation-edit"][data-key="number:{unmatched["number"]}"]').click();page.locator('[data-grade-part="0"][data-grade-input="estimate"]').fill('');page.locator('#grade-entry-form button[type="submit"]').click();page.locator('#simulation-course-filter').select_option('unknown');assert row(unmatched).is_visible();assert '1 missing assumptions' in page.locator('#simulation-coverage').inner_text();quick(unmatched,5.5);page.locator('#simulation-course-filter').select_option('all');save()

                # Labels are bilingual; changing language does not change assumptions.
                page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='de'");assert 'Szenarien speichern' in page.locator('.scenario-save-toolbar').inner_text();assert grade(b)=='5.10';page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='en'")
                page.reload();page.wait_for_selector('.metric');nav('simulation');unlock();assert page.locator('#simulation-select').input_value()==first_scene;assert grade(c)=='5.40' and grade(b)=='5.10'
                encrypted=Path(d,'grades.enc').read_text();assert 'fallbackGrade' not in encrypted and 'Planning at minus' not in encrypted;assert 'fallbackGrade' not in Path(d,'masterplan.json').read_text()
                assert not errors,errors;print('SIMULATION DEFAULTS BROWSER PASSED: sparse imports, non-destructive sigma, global fallback/local overrides/reset, unknown not zero, inline search/filter, draft retention, Save scenarios with pending edits, multiple scenarios/last selection after reload, encrypted persistence and DE/EN labels');browser.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
