"""Optional browser regression test with synthetic data and mocked local responses.

Run: python tests/browser_smoke.py  (requires playwright + Chromium)
Does not contact VVZAPI or touch user-data.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from sys import path as syspath
ROOT=Path(__file__).resolve().parents[1]
syspath.insert(0,str(ROOT))
from server import initial_state


def main():
    data=initial_state()
    rules=json.loads((ROOT/'guidelines/cse-guidelines.json').read_text(encoding='utf-8'))
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1400,'height':970})
        errors=[]
        page.on('pageerror',lambda err: errors.append(str(err)))
        html=(ROOT/'web/index.html').read_text(encoding='utf-8').replace('<script type="module" src="/app.js"></script>','').replace('<link rel="stylesheet" href="/styles.css">','')
        page.set_content(html)
        page.add_style_tag(content=(ROOT/'web/styles.css').read_text(encoding='utf-8'))
        page.evaluate('''([state,rules])=>{
          let saved=state;window.saveConflicts=0;
          window.externalChange=()=>{saved={...saved,revision:saved.revision+1,theme:'dark'};};
          window.fetch=async(url,opts={})=>{
            const u=String(url);
            if(u.includes('/api/vvz/search')) {
              const q=new URL(u,'http://localhost').searchParams.get('q');
              await new Promise(resolve=>setTimeout(resolve,q==='First'?160:20));
              return new Response(JSON.stringify({total:1,source:'mock',results:[{number:q,title:q,credits:6,semesters:{'2026W':111},offering:{unit_id:111,source_semester:'2026W',proxy:false}}]}));
            }
            if(u.includes('/api/state') && opts.method==='POST') {
              await new Promise(resolve=>setTimeout(resolve,80));
              if(JSON.parse(opts.body).revision!==saved.revision) {
                window.saveConflicts++;
                return new Response(JSON.stringify({error:'Revision conflict'}),{status:409});
              }
            }
            const value=u.includes('/api/guidelines')?rules:u.includes('/api/state')?(opts.method==='POST'?((saved=JSON.parse(opts.body)),(saved.revision+=1),saved):saved):u.includes('/api/vvz/times')?{status:'ready',meetings:[]}:u.includes('/api/vvz/dump/')?{available:true,phase:'ready',checking:false,lastChecked:1794180000, size:12345678,maxRequestsPerMinute:1}:{results:[]};
            return new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});
          }
        }''',[data,rules])
        page.add_script_tag(content=(ROOT/'web/app.js').read_text(encoding='utf-8'))
        page.set_default_timeout(7000)
        print('ready',flush=True)
        page.wait_for_selector('.metric')
        assert 'Mein tatsächliches Studium' in page.locator('#app').inner_text()
        page.evaluate('''async()=>{
          await Promise.all([save(s=>s.theme='dark'),save(s=>s.language='en'),save(s=>s.theme='light'),save(s=>s.language='de')]);
          if(window.saveConflicts)throw Error('Concurrent saves used stale revisions');
          if(state.revision!==4||state.theme!=='light'||state.language!=='de')throw Error('Queued save lost an edit');
        }''')
        page.evaluate('''async()=>{
          window.externalChange();
          await save(s=>s.language='en');
          if(state.language!=='de'||state.theme!=='dark'||window.saveConflicts!==1)throw Error('Conflict overwrote external data');
          await save(s=>s.theme='light');
          if(state.theme!=='light')throw Error('Save queue did not recover');
        }''')
        page.locator('[data-nav="catalog"]').click()
        page.evaluate('''()=>{
          document.querySelector('[name="q"]').value='First';document.querySelector('#search-form').requestSubmit();
          document.querySelector('[name="q"]').value='Second';document.querySelector('#search-form').requestSubmit();
        }''')
        page.wait_for_function('document.querySelector(".course-card .course-name")?.textContent==="Second"')
        page.wait_for_timeout(200)
        assert page.locator('.course-card .course-name').inner_text()=='Second'
        prompts=iter(['Example Course (synthetic)','DEMO-9999-00L'])
        page.on('dialog',lambda dialog: dialog.accept(next(prompts,'')))
        page.locator('[data-nav="catalog"]').click()
        page.locator('[data-action="manual-interest"]').click()
        page.wait_for_selector('.shortlist-item')
        page.locator('[data-nav="semesters"]').click()
        form=page.locator('#assign-course-form')
        form.locator('select[name="plan"]').select_option('actual')
        form.locator('select[name="semester"]').select_option('2026W')
        form.locator('select[name="role"]').select_option('extra')
        page.locator('[data-action="assign-interest"]').click()
        page.wait_for_function('state.actualPlan.courses.length===1')
        assert 'Example Course (synthetic)' in page.locator('.semester-col').first.inner_text()
        page.locator('[data-action="remove-course"][data-plan-id="actual"]').first.click()
        page.wait_for_function('state.actualPlan.courses.length===0')
        assert 'Example Course (synthetic)' not in page.locator('.semester-col').first.inner_text()
        assert 'Example Course (synthetic)' in page.locator('#assign-course-form').inner_text()
        page.locator('[data-action="assign-interest"]').click()
        page.wait_for_function('state.actualPlan.courses.length===1')
        page.locator('[data-nav="schedule"]').click()
        event_form=page.locator('#event-form')
        assert 'Example Course' in event_form.locator('select[name="course"]').inner_text()
        event_form.locator('select[name="day"]').select_option('2')
        event_form.locator('input[name="start"]').fill('08:15')
        event_form.locator('input[name="end"]').fill('10:00')
        event_form.locator('input[name="building"]').fill('HG')
        event_form.locator('input[name="room"]').fill('F 1')
        event_form.locator('button[type="submit"]').click()
        page.wait_for_function('state.actualPlan.courses[0].events.length===1')
        assert page.locator('.event').count()==1,page.locator('#toast').inner_text()
        assert 'HG' in page.locator('.event').first.inner_text()
        page.locator('[data-nav="dashboard"]').click()
        assert '0' in page.locator('.metric').first.inner_text()
        grade=page.evaluate('''() => calculateFinalGrade([
            {category:'core',parts:[{value:4,weight:100}]},
            {category:'core',parts:[{value:5,weight:100}]},
            ...Array.from({length:4},()=>({category:'specialisation',parts:[{value:4.5,weight:100}]})),
            {category:'elective',parts:[{value:5.5,weight:100}]},
            {category:'elective',parts:[{value:5.5,weight:100}]},
            {category:'thesis',parts:[{value:6,weight:100}]},
        ])''')
        assert grade['complete'] and grade['denominator']==14,grade
        assert abs(grade['value'] - 71/14)<1e-8,grade
        page.locator('[data-nav="settings"]').click()
        page.wait_for_selector('#dump-status')
        page.wait_for_function('document.querySelector("#dump-status").textContent.includes("Offline") || document.querySelector("#dump-status").textContent.includes("Lokale")')
        assert 'Maximal eine externe Anfrage' in page.locator('#app').inner_text()
        page.locator('[data-action="check-dump"]').click()
        page.wait_for_timeout(100)
        assert not errors,errors
        print('BROWSER SMOKE PASSED: shortlist, actual semester assign/remove, course dropdown, manual event, ECTS exclusion and official grade formula')
        browser.close()

if __name__=='__main__':main()
