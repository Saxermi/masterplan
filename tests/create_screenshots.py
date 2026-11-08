"""Capture real MasterPlan UI screenshots with synthetic demo-only data.

Optional developer dependency: pip install playwright, install Chromium separately.
Run: python tests/create_screenshots.py
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / 'docs' / 'screenshots'
SHOTS.mkdir(parents=True,exist_ok=True)


def course(number, title, semester, role, ects, **extra):
    return dict(id=number, number=number, title=title, semester=semester,
                role=role, ects=ects, status='planned', **({'events': [], **extra}))


def main():
    with tempfile.TemporaryDirectory(prefix='masterplan-screens-') as folder:
        from sys import path
        path.insert(0,str(ROOT))
        from server import initial_state
        demo = initial_state()
        demo['actualPlan']['courses'] = [
            course('DEMO-A-01','Numerical Modelling (demo)','2026W','core',6,
                   unitId=111111,sourceSemester='2026W',reviewAvailable=True,
                   events=[dict(day=0,start='09:15',end='11:00',building='HG',floor='E',room='33.1',source='manual')]),
            course('DEMO-A-02','Laboratory Methods (demo)','2026W','elective',4,
                   unitId=222222,sourceSemester='2026W',events=[]),
        ]
        demo['interests'] = [dict(id='demo-interest',number='DEMO-INT-01',title='Advanced Scientific Computing (demo)',ects=6,suggestedRole='specialisation',offerings={'2026W':333333},reviewAvailable=False)]
        physics = demo['plans'][0]
        physics['lockedSemesters'] = ['2026W']
        physics['courses'] = [
            course('D-001','Computational Methods in Physics','2026W','core',6,locked=True),
            course('D-002','Numerical Simulation','2026W','specialisation',6,locked=True),
            course('D-003','Mathematical Modelling','2027S','core',6,proxy=True,sourceSemester='2026S'),
            course('D-004','Fluid Mechanics Seminar','2027S','specialisation',3),
            course('D-005','Introduction to Astrophysics','2027S','extra',4),
            course('D-006','Computational Physics Project','2027W','project',8),
        ]
        fluids = demo['plans'][1]
        fluids['courses'] = [
            course('D-001','Computational Methods in Physics','2026W','core',6),
            course('D-010','Applied Fluid Mechanics','2027S','specialisation',6),
            course('D-011','Computational Fluid Dynamics','2027S','specialisation',6),
            course('D-012','Advanced Numerical Algorithms','2027W','elective',4),
        ]
        Path(folder, 'masterplan.json').write_text(json.dumps(demo),encoding='utf-8')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':980}, device_scale_factor=1)
            # Render the real frontend assets with a mocked local API, without a live server.
            html=(ROOT/'web/index.html').read_text(encoding='utf-8')
            html=html.replace('<script type="module" src="/app.js"></script>','').replace('<link rel="stylesheet" href="/styles.css">','')
            page.set_content(html)
            page.add_style_tag(content=(ROOT/'web/styles.css').read_text(encoding='utf-8'))
            guidelines=json.loads((ROOT/'guidelines/cse-guidelines.json').read_text(encoding='utf-8'))
            page.evaluate("""([state, guidelines]) => {
               window.fetch = async (url) => {
                 const u=String(url);
                 const data=u.includes('/api/guidelines') ? guidelines : u.includes('/api/vvz/dump/') ? {available:true,phase:'ready',checking:false,lastChecked:1794180000,size:12345678,maxRequestsPerMinute:1} : u.includes('/api/vvz/times') ? {status:'ready',source:'mock VVZ',meetings:[{day:0,start:'09:15',end:'11:00',building:'HG',floor:'E',room:'33.1',label:'Demo lecture',slotKey:'demo-slot-1'},{day:2,start:'13:15',end:'15:00',building:'ML',floor:'H',room:'48',label:'Demo exercises',slotKey:'demo-slot-2'}]} : u.includes('/api/vvz/search') ? {
                   results:[{number:'DEMO-CORE-01',rating:4.3,title:'Example Mathematical Core Course',title_english:'Example Mathematical Core Course',credits:9,language:'English',offering:{unit_id:99912,source_semester:'2026W',proxy:false}},
                   {number:'DEMO-CORE-02',title:'Example Engineering Core Course',title_english:'Example Engineering Core Course',credits:6,language:'English',offering:{unit_id:99913,source_semester:'2026W',proxy:false}}],
                   total:2, source:'demonstration only', eligibleCoreElective:true
                 } : state;
                 return new Response(JSON.stringify(data), {status:200, headers:{'Content-Type':'application/json'}})
               };
             }""",[demo,guidelines])
            page.add_script_tag(content=(ROOT/'web/app.js').read_text(encoding='utf-8'))
            page.wait_for_selector('.metric')
            page.screenshot(path=str(SHOTS/'01-dashboard.jpg'),full_page=True, type='jpeg', quality=78)
            for menu, file in [('Semesterplanung','02-semesters.jpg'),('Studienpläne','03-plans.jpg'),('Modulkatalog','04-catalog.jpg')]:
                page.locator('#nav').get_by_role('button',name=menu).first.click()
                page.wait_for_timeout(150)
                page.screenshot(path=str(SHOTS/file),full_page=True, type='jpeg', quality=78)
            # Real UI interactions: compare two different plans in the same spring semester.
            page.locator('#nav').get_by_role('button',name='Studienpläne').click()
            page.get_by_role('button',name='Semester vs. Semester').click()
            page.locator('#compare-left-plan').select_option('physics')
            page.locator('#compare-right-plan').select_option('fluids')
            page.locator('#compare-left-sem').select_option('2027S')
            page.locator('#compare-right-sem').select_option('2027S')
            assert page.locator('.compare-pair').count() >= 4
            assert page.get_by_text('Mathematical Modelling').count() >= 1
            page.screenshot(path=str(SHOTS/'05-semester-comparison.jpg'),full_page=True,type='jpeg',quality=78)
            # Real UI interactions: browse eligible ETH MSc Core Courses as CSE electives.
            page.locator('#nav').get_by_role('button',name='Modulkatalog').click()
            page.locator('[data-action="browse-eligible-core"]').click()
            page.locator('#search-form').evaluate('(form) => form.requestSubmit()')
            page.wait_for_selector('.course-card')
            assert page.locator('#search-form select[name="programme"]').input_value() == 'eligible-core-all'
            assert page.locator('#search-form select[name="category"]').input_value() == 'eligible-core'
            assert page.get_by_text('MSc-Core → potenzielles CSE-Elective').count() >= 1
            page.screenshot(path=str(SHOTS/'06-eligible-cores.jpg'),full_page=True,type='jpeg',quality=78)
            page.locator('#nav').get_by_role('button',name='Stundenplan').click()
            page.wait_for_selector('.meeting-options',timeout=10000)
            assert page.locator('.meeting-option').count() >= 2
            assert page.get_by_role('link',name='CourseReview').count() >= 1
            page.screenshot(path=str(SHOTS/'07-api-timetable.jpg'),full_page=True,type='jpeg',quality=78)
            page.locator('[data-nav="settings"]').click()
            page.wait_for_selector('#dump-status')
            page.wait_for_timeout(160)
            page.screenshot(path=str(SHOTS/'08-offline-catalog.jpg'),full_page=True,type='jpeg',quality=78)
            browser.close()
            for path in sorted(SHOTS.glob('*.jpg')):
                print(path.name, path.stat().st_size,'bytes')

if __name__ == '__main__': main()
