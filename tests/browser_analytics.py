"""Real UI imports, formulas, exports, insights and precise repeated calendar meetings.
All fixtures are synthetic. Set SCREENSHOT_DIR to capture review evidence.
"""
import json
import os
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from browser_allocations import baseline
from browser_semester_flow import Handler,Store,LocalCatalog,VvzCache,VvzDump,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS,make_db


def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);db=root/'catalog.sqlite';make_db(db)
        with sqlite3.connect(db) as conn:
            for field in ['abstract','abstract_english','objective','objective_english','content','content_english']:
                conn.execute(f'ALTER TABLE learningunit ADD COLUMN {field} TEXT')
            conn.execute("UPDATE learningunit SET abstract_english='Synthetic course description for review.',objective_english='Design and test reliable software systems.' WHERE id=111")
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(root/'personal')
        http.catalog=LocalCatalog(db,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS)
        http.vvz=VvzCache(root/'cache');http.vvz_dump=VvzDump(root/'cache',http.vvz,http.catalog)
        state=baseline();courses=state['actualPlan']['courses'];first=courses[0];first.update(title='Software Engineering (demo)',unitId=111,sourceSemester='2026W',offerings={'2026W':111})
        http.store.save(state);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1540,'height':1100});page.set_default_timeout(10000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                def screenshot(name,selector):
                    if os.getenv('SCREENSHOT_DIR'):
                        path=Path(os.environ['SCREENSHOT_DIR']);path.mkdir(parents=True,exist_ok=True)
                        page.locator(selector).screenshot(path=str(path/name),type='jpeg',quality=85)
                def nav(where):page.locator(f'[data-nav="{where}"]').click()
                def unlock():
                    page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-analytics-vault');page.locator('#grades-unlock-form button').click();page.wait_for_selector('[data-action="grade-save"]')
                def part(index,field,value):page.locator(f'[data-grade-part="{index}"][data-grade-input="{field}"]').fill(str(value))
                def preview(data,choice=None):
                    page.locator('#exchange-form [name="json"]').fill(json.dumps(data))
                    if choice:page.locator('#exchange-form [name="useActual"]').select_option(choice)
                    page.locator('#exchange-form button[type="submit"]').click();page.wait_for_selector('#exchange-preview')
                def apply_import():page.locator('[data-action="exchange-apply"]').click();page.wait_for_selector('#exchange-preview',state='detached')
                def statistical_scenario(name,factor,inherit):
                    f=page.locator('#statistics-scenario-form');f.locator('[name="name"]').fill(name);f.locator('[name="factor"]').fill(str(factor));f.locator('[name="useActual"]').select_option(inherit);f.locator('button').click();page.wait_for_selector('#simulation-select')
                def export(action):
                    with page.expect_download() as result:page.locator(f'[data-action="{action}"]').click()
                    return Path(result.value.path()).read_text()
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');nav('grades');unlock()
                # Same custom language for actual marks and simulation assumptions.
                page.locator('[data-action="grade-add"]').click();page.locator('[data-grade-link]').select_option(first['id']);page.locator('[data-action="formula-two"]').click()
                part(0,'value',5);part(1,'estimate',4);page.locator('[data-grade-input="bonus"]').fill('0.25')
                assert page.locator('[data-projected-grade]').inner_text()=='4.45'
                page.locator('[data-action="formula-three"]').click();part(1,'value',4.5);part(2,'estimate',4)
                assert page.locator('[data-projected-grade]').inner_text()=='4.55'
                screenshot('20-custom-grade-formula.jpg','#grade-entry-form')
                # In-formula additive bonus is not counted twice; arbitrary code rejected.
                page.locator('[data-grade-input="bonusPlacement"]').select_option('formula');page.locator('[data-grade-input="formula"]').fill('max(F, 0.8*F + 0.2*M1) + B')
                assert page.locator('[data-projected-grade]').inner_text()=='4.45'
                page.locator('[data-grade-input="formula"]').fill('window.alert(1)');assert page.locator('#grade-preview [role="status"]').count()==1
                page.locator('[data-action="formula-two"]').click();page.locator('[data-grade-input="bonusPlacement"]').select_option('after');page.locator('[data-grade-input="bonus"]').fill('0');part(1,'value',5.5)
                page.locator('#grade-entry-form button[type="submit"]').click()
                nav('simulation')
                stats={'schemaVersion':1,'kind':'masterplan-statistics','name':'Demo PDF — exam statistics','courses':[{'number':c['number'],'title':c['title'],'semester':c['semester'],'mean':5,'stddev':.5,'sampleSize':120,'source':{'document':'Synthetic exam statistics.pdf','page':1}} for c in courses]}
                preview(stats);assert '15 unambiguously matched' in page.locator('#exchange-preview').inner_text()
                page.locator('#exchange-form [name="json"]').fill('{invalid');assert page.locator('#exchange-preview').count()==0
                preview(stats)
                # Prepared prompts describe PDF extraction, not an app-side PDF parser.
                prompts=page.locator('details').filter(has=page.locator('textarea[aria-label="statistics prompt de"]'));prompts.locator('summary').click()
                assert 'never invent' in page.locator('textarea[aria-label="statistics prompt en"]').input_value()
                screenshot('21-json-statistics-import.jpg','#exchange-panel');apply_import()
                statistical_scenario('One sigma below average (demo)',-1,'no');assert page.locator('#private-final .metric').inner_text()=='4.50'
                page.locator('#private-final').scroll_into_view_if_needed();screenshot('22-statistical-master-grade.jpg','#private-final')
                # Selected adjustment does not change unselected assumptions.
                adjust=page.locator('#statistics-adjust-form');[box.uncheck() for box in adjust.locator('[name="modules"]').all()];adjust.locator('[name="modules"]').first.check();adjust.locator('[name="factor"]').fill('0');adjust.locator('button').click()
                assert page.locator('#private-final .metric').inner_text()=='4.57'
                statistical_scenario('Keep actual results (demo)',-1,'yes');assert page.locator('#private-final .metric').inner_text()=='4.64'
                key='number:'+first['number'];page.locator(f'[data-action="simulation-edit"][data-key="{key}"]').click()
                assert page.locator('[data-grade-input="formula"]').get_attribute('readonly') is not None
                assert page.locator('[data-grade-part="1"][data-grade-input="value"]').input_value()=='5.5';page.locator('[data-action="grade-draft-cancel"]').click()
                raw={'schemaVersion':1,'kind':'masterplan-grade-scenario','name':'Imported assumptions (demo)','courses':[{'number':c['number'],'semester':c['semester'],'grade':4.8} for c in courses]}
                preview(raw);page.locator('[data-action="exchange-apply"]').click();assert page.locator('#exchange-preview').count()==1
                page.locator('#exchange-form [name="useActual"]').select_option('yes');apply_import();assert page.locator('#private-final .metric').inner_text()=='4.90'
                # Missing deviations stay unknown; no complete Master grade is invented.
                stats['name']='Missing deviation';stats['courses'][0]['stddev']=None;preview(stats);apply_import();page.locator('#statistics-scenario-form [name="dataset"]').select_option(index=1)
                statistical_scenario('Unknown standard deviation',-1,'no');assert page.locator('#private-final .metric').inner_text()=='—';assert 'Statistical assumption unknown' in page.locator('#app').inner_text()
                page.locator('[data-action="grade-save"]').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('encrypted and saved')")
                encrypted=Path(root/'personal'/'grades.enc').read_text();assert 'Synthetic exam statistics.pdf' not in encrypted
                assert 'Synthetic exam statistics.pdf' not in Path(root/'personal'/'masterplan.json').read_text()
                # Public insights are separate from encrypted marks/statistics.
                nav('semesters');page.locator(f'[data-drag-course="{first["id"]}"] [data-action="course-details"]').click();page.wait_for_selector('.course-detail-text')
                assert 'Design and test reliable software systems.' in page.locator('#app').inner_text()
                note='Review testing prerequisites before HS 2026. (synthetic note)';page.locator('#module-notes-form textarea').fill(note);page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='de'");assert page.locator('#module-notes-form textarea').input_value()==note;page.locator('#lang-toggle').click();page.wait_for_function("()=>document.documentElement.lang==='en'");page.locator('#module-notes-form button').click()
                page.wait_for_function("async()=>Object.values((await(await fetch('/api/state')).json()).moduleInsights||{}).some(x=>x.notes.includes('synthetic note'))")
                nav('plans');data=json.loads(export('export-study-json'));assert len(data['courses'])==15;assert all('vvz.ethz.ch' in c['vvzUrl'] for c in data['courses']);assert 'personalNotes' not in json.dumps(data) and '5.5' not in json.dumps(data)
                assert export('export-study-csv').startswith('"semester","number"')
                page.locator('#export-notes').check();context=json.loads(export('export-preparation'));out=next(c for c in context['courses'] if c['id']==first['id']);assert out['personalNotes']==note;assert out['courseInformation']['objective_english']=='Design and test reliable software systems.'
                prep={'schemaVersion':1,'kind':'masterplan-preparation','courses':[{'number':first['number'],'semester':first['semester'],'assessment':'Demo: suitable after reviewing programming foundations.','confidence':'medium','prerequisites':['Programming and algorithms'],'gaps':['Review automated testing'],'recommendations':['Complete a small testing exercise before semester start.'],'source':{'url':out['vvzUrl']}}]}
                preview(prep);apply_import();nav('semesters');page.locator(f'[data-drag-course="{first["id"]}"] [data-action="course-details"]').click();page.wait_for_selector('#preparation-assessment');assert page.locator('#module-notes-form textarea').input_value()==note
                screenshot('23-course-notes-preparation.jpg','#app')
                # Real-time geometry: Tue 16–18, quarter-hour starts, multiple sessions, conflicts.
                nav('schedule');page.locator('#schedule-sem').select_option('2026W');page.locator(f'[data-schedule-course="{first["id"]}"]').click();page.locator('.daycell[data-day="1"][data-start="16:00"]').click()
                f=page.locator('#event-form');f.locator('[name="end"]').fill('18:00');f.locator('[name="building"]').fill('HG');f.locator('[name="floor"]').fill('F');f.locator('[name="room"]').fill('5');f.locator('button[type="submit"]').click();page.wait_for_selector('.event')
                event=page.locator('.event').first;assert event.bounding_box()['height']>=129;assert '16:00–18:00' in event.inner_text() and 'HG F 5' in event.inner_text()
                page.locator(f'[data-schedule-course="{first["id"]}"]').drag_to(page.locator('.daycell[data-day="2"][data-start="10:00"]'));f.locator('[name="start"]').fill('10:15');f.locator('[name="end"]').fill('11:45');f.locator('button[type="submit"]').click();page.wait_for_function("()=>document.querySelectorAll('.event').length===2")
                q=page.locator('[data-event-start="615"]');assert abs(q.bounding_box()['height']-96.5)<2
                assert abs(q.bounding_box()['y']-q.locator('..').bounding_box()['y']-17.75)<2
                f.locator('[name="course"]').select_option(courses[1]['id']);f.locator('[name="day"]').select_option('1');f.locator('[name="start"]').fill('17:00');f.locator('[name="end"]').fill('19:00');f.locator('button[type="submit"]').click();page.wait_for_function("()=>document.querySelectorAll('.event').length===3")
                assert page.locator('[data-event-columns="2"]').count()==2
                screenshot('24-multiple-calendar-meetings.jpg','.schedule-wrap')
                page.reload();page.wait_for_selector('.metric');nav('schedule');page.locator('#schedule-sem').select_option('2026W');assert page.locator('.event').count()==3
                nav('simulation');unlock();assert page.locator('#simulation-select option').count()==4
                assert not errors,errors
                print('ANALYTICS BROWSER PASSED: adaptive formulas, actual-mark protection, validated JSON imports, sigma scenarios, selected adjustment, unknown deviations, encrypted roundtrip, chronological exports, preparation context, persistent notes/assessments, Tuesday 16–18 and quarter-hour overlapping repeated meetings')
                browser.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
