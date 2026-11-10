"""Real HTTP/browser checks for invalid allocations, editors and scenario isolation.

Uses synthetic data and a temporary personal folder. No upstream catalogue traffic.
"""
import copy
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
from unittest.mock import Mock
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import Handler, Store, initial_state

_serial=0
def course(role,ects,status='planned',**changes):
    global _serial
    _serial+=1
    c=dict(id=f'c{_serial}',number=f'TEST-{_serial}',title=f'Synthetic {role} {_serial}',role=role,ects=ects,status=status,semester='2026W',events=[])
    c.update(changes)
    return c


def baseline():
    s=initial_state();s['language']='en'
    s['actualPlan']['courses']=[course('core',6),course('core',6),
        *[course('specialisation',4,subtype='lecture',specialisation='Physics') for _ in range(4)],
        course('specialisation',2,subtype='seminar',specialisation='Physics'),course('elective',22),course('elective',22),
        course('case',3,number='CASE'),course('case',3,number='CASE',semester='2027S'),course('project',8),course('sip',2),course('thesis',30),course('scientific',0,status='completed')]
    return s


def main():
    with tempfile.TemporaryDirectory() as d:
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.store=Store(d)
        server.vvz_dump=Mock();server.vvz_dump.status.return_value={'available':False,'phase':'missing'}
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(10000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_selector('.metric')
                def load(s):
                    code=page.evaluate("async(s)=>(await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s)})).status",s)
                    assert code==200,server.store.get()
                    page.reload();page.wait_for_selector('.metric');page.locator('[data-nav="requirements"]').click()
                def check(key,value):
                    assert page.locator(f'[data-requirement="{key}"]').first.get_attribute('data-potential')==str(value).lower(),key
                s=baseline();load(s)
                for key in ['core','spec','elective','main','total','case','project','thesis','sip','scientific']:check(key,True)
                # User-requested combination: one core, too few specialisation lectures, many electives.
                s=baseline();s['actualPlan']['courses']=[c for c in s['actualPlan']['courses'] if c['role'] not in ['core','specialisation']]
                s['actualPlan']['courses'] += [course('core',18),course('specialisation',18,subtype='lecture'),*[course('elective',20) for _ in range(6)]]
                load(s);check('core',False);check('spec',False);check('elective',True);check('total',True)
                assert page.locator('[data-audit-code="transcript-limit"]').count()==1
                # Warning-only ceiling: otherwise complete plan remains valid at 160 credits.
                s=baseline();s['actualPlan']['courses'].append(course('elective',40));load(s)
                check('total',True);assert 'meets the checked requirements' in page.locator('#allocation-audit').inner_text()
                assert page.locator('[data-audit-code="transcript-limit"]').count()==1
                # Extra seminar cannot replace a missing lecture.
                s=baseline();next(c for c in s['actualPlan']['courses'] if c.get('subtype')=='lecture')['subtype']='seminar'
                load(s);check('spec',False)
                # Surplus cores are diagnosed, not blocked as a draft.
                s=baseline();s['actualPlan']['courses'].append(course('core',6));load(s);check('core',False)
                assert page.locator('[data-audit-code="maxCourses"]').count()==1
                # Same module in a second semester counts once and has a visible warning.
                s=baseline();c=s['actualPlan']['courses'][0];s['actualPlan']['courses'].append(dict(c,id='repeat',semester='2027S',role='elective'))
                load(s);assert page.locator('[data-audit-code="duplicate-credit"]').count()==1
                assert page.locator('[data-requirement="total"]').first.locator('.row').nth(1).inner_text().startswith('0 / 120')
                # Planned work must never be labelled completed.
                s=baseline();load(s);assert page.locator('[data-requirement="total"]').first.get_attribute('data-done')=='false'
                for c in s['actualPlan']['courses']:c['status']='completed'
                load(s);assert page.locator('[data-requirement="total"]').first.get_attribute('data-done')=='true'
                # Course field markup is escaped in both audit and semester pages.
                s=baseline();s['actualPlan']['courses'][0]['title']='<img src=x onerror="window.injected=true">'
                load(s);page.locator('[data-nav="semesters"]').click();assert page.locator('#app img').count()==0
                assert not page.evaluate('()=>window.injected===true')
                # A real editor path can create a specialisation seminar.
                s=initial_state();s['language']='en';s['interests']=[{'id':'placeholder','title':'Placeholder','ects':0,'offerings':{}}]
                load(s);page.locator('[data-nav="semesters"]').click()
                answers=iter(['Seminar fixture','TEST-SEM','2026W','2','specialisation','planned','seminar','Physics'])
                def dialog(e):
                    if e.type=='confirm':e.dismiss()
                    else:e.accept(next(answers))
                page.on('dialog',dialog);page.locator('[data-action="manual-course"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).actualPlan.courses.length===1)")
                saved=server.store.get();assert saved['actualPlan']['courses'][0]['subtype']=='seminar';assert saved['actualPlan']['courses'][0]['specialisation']=='Physics'
                page.remove_listener('dialog',dialog)
                # An imaginary completed course in a scenario must not enter actual history.
                s=initial_state();s['language']='en';s['activePlan']='physics';s['interests']=[{'id':'placeholder','title':'Placeholder','ects':0,'offerings':{}}]
                load(s);page.locator('[data-nav="semesters"]').click()
                answers=iter(['Hypothetical completion','TEST-HYP','2026W','6','core','completed'])
                page.on('dialog',dialog);page.locator('[data-action="manual-course"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).plans[0].courses.length===1)")
                assert server.store.get()['history']==[];assert server.store.get()['actualPlan']['courses']==[]
                page.remove_listener('dialog',dialog)
                # Editing a real completion back to planned removes stale history.
                s=initial_state();s['language']='en';c=course('core',6,status='completed');s['actualPlan']['courses']=[c];s['history']=[dict(c,locked=True)]
                load(s);page.locator('[data-nav="semesters"]').click()
                answers=iter([c['title'],c['number'],'2026W','6','core','planned'])
                page.on('dialog',dialog);page.locator('[data-action="edit-course"]').click()
                page.wait_for_function("async()=>((await (await fetch('/api/state')).json()).history.length===0)")
                assert server.store.get()['actualPlan']['courses'][0]['status']=='planned'
                assert not errors,errors
                print('ALLOCATION BROWSER PASSED: real API imports, invalid distributions, warning-only >130 ECTS, duplication, planned/completed, escaping, seminar editor, scenario isolation and history correction')
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':main()
