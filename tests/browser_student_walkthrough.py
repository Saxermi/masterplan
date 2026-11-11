"""Student-style walkthrough of the three ODS scenarios using the actual interface.
Only exam statistics are synthetic; imported plans derive from the user's spreadsheet.
"""
import json,os,shutil,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import Mock
from playwright.sync_api import sync_playwright
from browser_allocations import ROOT,Handler,Store


def main():
 with tempfile.TemporaryDirectory() as d:
  http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d);http.vvz_dump=Mock();http.vvz_dump.status.return_value={'available':False,'phase':'missing'}
  state=http.store.get();state['language']='en';http.store.save(state);original=http.store.get();thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1600,'height':1200},locale='en-GB');page.set_default_timeout(12000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def nav(where):page.locator(f'[data-nav="{where}"]').click()
    def unlock():page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-student-password');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#exchange-form' if page.locator('#exchange-form').count() else '[data-action="grade-add"]')
    def shot(name,selector):
     if os.getenv('SCREENSHOT_DIR'):
      p=Path(os.environ['SCREENSHOT_DIR']);p.mkdir(parents=True,exist_ok=True);page.locator(selector).screenshot(path=str(p/name),type='jpeg',quality=85)
    page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');nav('plans')
    source=ROOT/'docs/examples/ods-scenarios/all-three-study-plans.json';page.locator('#study-plan-file').set_input_files(source);page.locator('#study-plan-import-form button').click();page.wait_for_selector('#study-plan-preview');shot('50-three-study-plans-import.jpg','#study-plan-transfer');page.locator('[data-action="study-plan-apply"]').click();page.wait_for_function("async()=>((await(await fetch('/api/state')).json()).plans.length===5)")
    saved=http.store.get();assert saved['actualPlan']==original['actualPlan'];assert saved['history']==original['history'];plans=saved['plans'][-3:];assert len({c['id'] for p in plans for c in p['courses']})==66
    # Walk each semester board and roundtrip each plan independently.
    for p in plans:
     page.locator('#export-plan').select_option(p['id'])
     with page.expect_download() as download:page.locator('[data-action="export-study-json"]').click()
     out=json.loads(Path(download.value.path()).read_text());assert len(out['courses'])==22;assert len(out['plan']['semesters'])==6;assert sum(c['gradingMode']=='pass-fail' for c in out['courses'])==4;assert all('vvz.ethz.ch' in c['vvzUrl'] for c in out['courses'])
    with page.expect_download() as download:page.locator('[data-action="export-study-all"]').click()
    bundle=json.loads(Path(download.value.path()).read_text());assert len(bundle['plans'])==6
    page.locator('[data-nav="semesters"]').click();assert page.locator('[data-drag-course]').count()==22
    # Create synthetic statistics for every numerical module/term in the three plans.
    rows={}
    for p in plans:
     for c in p['courses']:
      if c['gradingMode']=='numeric':rows[(c['number'],c['semester'])]=dict(number=c['number'],semester=c['semester'],mean=5,stddev=.5,passRate=85,source={'document':'SYNTHETIC walkthrough fixture'})
    nav('simulation');page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-student-password');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#exchange-form')
    stats=dict(schemaVersion=1,kind='masterplan-statistics',name='Synthetic statistics — not real exam results',courses=list(rows.values()));page.locator('#exchange-form [name="json"]').fill(json.dumps(stats));page.locator('#exchange-form button').click();page.locator('[data-action="exchange-apply"]').click();page.wait_for_selector('#statistics-scenario-form')
    scene_ids=[]
    for index,p in enumerate(plans):
     f=page.locator('#statistics-scenario-form');f.locator('[name="plan"]').select_option(p['id']);f.locator('[name="name"]').fill(p['name']+' — practice');f.locator('[name="useActual"]').select_option('no');f.locator('button[type="submit"]').click();page.wait_for_selector('#simulation-select');scene_ids.append(page.locator('#simulation-select').input_value())
     assert page.locator('#private-final .metric').inner_text()=='5.00'
     assert page.locator('.simulation-outcome-form').count()==4
     page.locator('#simulation-course-filter').select_option('pending-outcome');assert page.locator('[data-simulation-row]:visible').count()==4;page.locator('#simulation-course-filter').select_option('all')
     for outcome in page.locator('.simulation-outcome-form').all():outcome.locator('[name="outcome"]').select_option('pass');outcome.locator('button').click()
     admission=next(c for c in p['courses'] if c['role']=='requirement');page.locator(f'[data-action="simulation-edit"][data-key="number:{admission["number"]}"]').click();assert page.locator('[data-grade-input="category"]').input_value()=='excluded';page.locator('[data-action="grade-draft-cancel"]').click()
     numeric=[c for c in p['courses'] if c['gradingMode']=='numeric']
     for i,c in enumerate(numeric):
      k='number:'+c['number'];row=page.locator(f'[data-simulation-row="{k}"]');factor=[-1,0,1][i%3];row.locator(f'[data-action="simulation-course-sigma"][data-factor="{factor}"]').click();assert row.locator('[data-simulation-grade]').inner_text()==f'{5+.5*factor:.2f}'
     # Restore one module to global control and verify other course-level settings persist.
     last=numeric[-1];row=page.locator(f'[data-simulation-row="number:{last["number"]}"]');row.locator('[data-action="simulation-course-global"]').click();f=page.locator('#statistics-adjust-form');f.locator('[name="factor"]').fill('1');f.locator('button[type="submit"]').click();assert row.locator('[data-simulation-grade]').inner_text()=='5.50'
     first=numeric[0];assert page.locator(f'[data-simulation-row="number:{first["number"]}"] [data-simulation-grade]').inner_text()=='4.50'
     if index==2:
      page.locator('[data-action="simulation-sigma-global-all"]').click();assert all(page.locator(f'[data-simulation-row="number:{c["number"]}"] [data-simulation-grade]').inner_text()=='5.50' for c in numeric)
     page.get_by_role('button',name='Save scenarios',exact=True).click();page.wait_for_selector('[data-scenario-save-state="saved"]')
     if index==0:page.locator('#simulation-course-filter').select_option('pass-fail');shot('51-pass-fail-outcomes.jpg','#simulation-courses');page.locator('#simulation-course-filter').select_option('all');page.locator('#simulation-course-search').fill('AI in');shot('52-individual-course-sigma.jpg','#simulation-courses');page.locator('#simulation-course-search').fill('')
    first_outcome=page.locator('.simulation-outcome-form').first;first_outcome.locator('[name="outcome"]').select_option('pending');first_outcome.locator('button').click();page.locator('.simulation-outcome-form').first.locator('[name="outcome"]').select_option('pass');page.get_by_role('button',name='Save scenarios',exact=True).click();page.wait_for_selector('[data-scenario-save-state="saved"]')
    page.reload();page.wait_for_selector('.metric');nav('simulation');page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-student-password');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#simulation-select');assert page.locator('#simulation-select option').count()==3;assert page.locator('#simulation-select').input_value()==scene_ids[-1]
    for scene in scene_ids:
     page.locator('#simulation-select').select_option(scene);assert all(x.input_value()=='pass' for x in page.locator('.simulation-outcome-form select').all())
    # A real pass/fail entry needs no invented numeric component.
    nav('grades');page.locator('[data-action="grade-add"]').click();page.locator('[data-grade-input="name"]:not([data-grade-part])').fill('Pass/fail seminar');page.locator('[data-grade-input="number"]').fill('401-5810-00L');page.locator('[data-grade-input="category"]').select_option('specialisation-seminar');page.locator('[data-grade-input="gradingMode"]').select_option('pass-fail');page.locator('[data-grade-input="outcome"]').select_option('pass');page.locator('#grade-entry-form button[type="submit"]').click();assert 'Pass' in page.locator('#app').inner_text();page.locator('[data-action="grade-save"]').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('encrypted and saved')")
    # The optional delivered grade file is importable too, including P/F outcomes.
    nav('simulation');page.locator('#exchange-form [name="plan"]').select_option(plans[0]['id']);page.locator('#exchange-file').set_input_files(ROOT/'docs/examples/ods-scenarios/ods-main-grade-assumptions.json');page.wait_for_function("()=>document.querySelector('#exchange-form [name=json]').value.includes('masterplan-grade-scenario')");page.locator('#exchange-form [name="useActual"]').select_option('no');page.locator('#exchange-form button').click();page.wait_for_selector('#exchange-preview');assert 'Pass / Fail' in page.locator('#exchange-preview').inner_text();page.locator('[data-action="exchange-apply"]').click();assert page.locator('#private-final .metric').inner_text()=='5.00';assert page.locator('#simulation-select option').count()==4;assert all(x.input_value()=='pass' for x in page.locator('.simulation-outcome-form select').all())
    assert not errors,errors;print('STUDENT WALKTHROUGH PASSED: 3 ODS plans, safe imports, 6-semester lossless exports, 54 individual numerical sigma controls, 12 pass/fail outcomes, global independence, encrypted reload and real pass/fail entry');b.close()
  finally:http.shutdown();http.server_close();thread.join(timeout=2)
if __name__=='__main__':main()
