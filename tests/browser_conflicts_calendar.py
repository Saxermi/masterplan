"""Explicit statistics conflict resolution and time-first calendar selection over real HTTP.
Fixtures are synthetic; SCREENSHOT_DIR captures review evidence without personal data.
"""
import copy
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
        state=baseline();courses=state['actualPlan']['courses'];first,second,locked=courses[:3];first['title']='Software Engineering (demo)';second['title']='Computational Physics (demo)';locked['locked']=True
        physics=next(p for p in state['plans'] if p['id']=='physics');physics['courses']=[dict(copy.deepcopy(c),id='physics-'+c['id'],semester='2027W') for c in [first,second]]
        http.store.save(state);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM') or shutil.which('chromium'),args=['--no-sandbox']);page=browser.new_page(viewport={'width':1500,'height':1400},locale='en-GB');page.set_default_timeout(10000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                def shot(name,selector):
                    if os.getenv('SCREENSHOT_DIR'):
                        folder=Path(os.environ['SCREENSHOT_DIR']);folder.mkdir(exist_ok=True,parents=True);page.locator(selector).screenshot(path=str(folder/name),type='jpeg',quality=85)
                def nav(where):page.locator(f'[data-nav="{where}"]').click()
                def unlock():page.locator('#grades-unlock-form [name="password"]').fill('Synthetic-conflict-vault');page.locator('#grades-unlock-form button').click();page.wait_for_selector('#exchange-form')
                def row(c,semester,mean,n,passed,doc):return dict(number=c['number'],title=c['title'],semester=semester,mean=mean,stddev=.5,sampleSize=n,passRate=passed,source={'document':doc,'page':1})
                def choose(scope,key,value,context='import'):page.locator(f'[data-statistics-choice="{scope}"][data-statistics-context="{context}"][data-statistics-key="{key}"]').select_option(str(value))
                page.goto(f'http://127.0.0.1:{http.server_port}');page.wait_for_selector('.metric');nav('simulation');unlock()
                data=dict(schemaVersion=1,kind='masterplan-statistics',name='Synthetic conflicting PDF records',courses=[row(first,'2026W',5,120,85,'First source.pdf'),row(first,'2026W',4.6,50,70,'Alternative source.pdf'),row(second,'2024W',4.2,80,60,'Older source.pdf'),row(second,'2025W',5.2,100,95,'Recent source.pdf')])
                page.locator('#exchange-form [name="json"]').fill(json.dumps(data));page.locator('#exchange-form button').click();page.wait_for_selector('#exchange-preview')
                assert page.locator('[data-statistics-choice]').count()==2
                page.locator('[data-action="exchange-apply"]').click();assert page.locator('#exchange-preview').count()==1;assert page.locator('#statistics-scenario-form').count()==0
                first_key='number:'+first['number']+'@2026W';second_key='number:'+second['number']+'@2026W'
                choose('row',first_key,1);choose('course',second_key,3)
                assert '0 unresolved conflicts' in page.locator('[data-statistics-conflicts="import"]').inner_text()
                assert '70%' in page.locator('#exchange-preview').inner_text()
                shot('30-statistics-conflict-choice.jpg','#exchange-preview')
                page.locator('[data-action="exchange-apply"]').click();page.wait_for_selector('#statistics-scenario-form')
                form=page.locator('#statistics-scenario-form');form.locator('[name="name"]').fill('Chosen source records');form.locator('[name="useActual"]').select_option('no');form.locator('button').click();page.wait_for_selector('#simulation-select')
                for c,grade,rate,source in [(first,'4.60','70%','Alternative source.pdf'),(second,'5.20','95%','Recent source.pdf')]:
                    card=page.locator('.card').filter(has=page.locator(f'[data-action="simulation-edit"][data-key="number:{c["number"]}"]')).last
                    text=card.inner_text();assert grade in text and rate in text and source in text,text
                # Another target semester asks for its own ambiguous historical choice.
                form.locator('[name="plan"]').select_option('physics');new_key='number:'+second['number']+'@2027W'
                assert page.locator(f'[data-statistics-key="{new_key}"]').input_value()=='';choose('course',new_key,2,'library')
                page.locator('[data-action="grade-save"]').click();page.wait_for_function("()=>document.querySelector('#toast').textContent.includes('encrypted and saved')")
                assert 'Alternative source.pdf' not in Path(d,'grades.enc').read_text();assert 'passRate' not in Path(d,'masterplan.json').read_text()
                nav('dashboard');nav('simulation');unlock()
                assert page.locator(f'[data-statistics-key="{first_key}"][data-statistics-context="library"]').input_value()=='1'
                assert page.locator(f'[data-statistics-key="{second_key}"][data-statistics-context="library"]').input_value()=='3'
                # Both original rows remain available after encrypted persistence.
                assert page.locator(f'[data-statistics-key="{first_key}"] option').count()==3
                nav('schedule');page.locator('#schedule-sem').select_option('2026W')
                def drag(day,start_hour,start_offset,end_hour,end_offset):
                    cell=page.locator(f'.daycell[data-day="{day}"][data-start="{start_hour:02d}:00"]');cell.scroll_into_view_if_needed();box=cell.bounding_box();x=box['x']+box['width']*.5;y=box['y']+start_offset/60*67+.2;end=box['y']+(end_hour-start_hour)*67+end_offset/60*67+.2
                    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,end,steps=8);assert page.locator('.calendar-time-selection').count()==1
                    if day==1:shot('33-calendar-range-selection.jpg','.schedule-wrap')
                    page.mouse.up();page.wait_for_selector('#calendar-selection-dialog[open]')
                def save_meeting():page.locator('#calendar-selection-form button[type="submit"]').click();page.wait_for_selector('#calendar-selection-dialog',state='detached')
                drag(1,16,0,18,0);f=page.locator('#calendar-selection-form');assert f.locator('[name="start"]').input_value()=='16:00';assert f.locator('[name="end"]').input_value()=='18:00';assert f.locator('[name="course"]').input_value()==''
                assert f.locator(f'option[value="{locked["id"]}"]').get_attribute('disabled') is not None
                f.locator('[name="course"]').select_option(first['id']);assert page.locator('#calendar-selection-vvz a').count()>0
                f.locator('[name="building"]').fill('HG');f.locator('[name="floor"]').fill('F');f.locator('[name="room"]').fill('5');shot('31-mark-time-assign-module.jpg','#calendar-selection-dialog');save_meeting()
                assert http.store.get()['actualPlan']['courses'][0]['events'][0]['start']=='16:00';assert page.locator('.event').count()==1
                drag(2,10,15,11,45);f=page.locator('#calendar-selection-form');assert f.locator('[name="start"]').input_value()=='10:15';assert f.locator('[name="end"]').input_value()=='11:45';f.locator('[name="course"]').select_option(first['id'])
                # Native dialog survives a language rerender without losing the selection.
                page.evaluate("()=>document.querySelector('#lang-toggle').click()");page.wait_for_function("()=>document.documentElement.lang==='de'");assert f.locator('[name="course"]').input_value()==first['id'];assert f.locator('[name="start"]').input_value()=='10:15';save_meeting();assert page.locator('.event').count()==2
                drag(3,14,30,13,15);f=page.locator('#calendar-selection-form');assert f.locator('[name="start"]').input_value()=='13:15';assert f.locator('[name="end"]').input_value()=='14:30';page.keyboard.press('Escape');page.wait_for_selector('#calendar-selection-dialog',state='detached');assert page.locator('.event').count()==2
                # Keyboard activation opens the same editable time-first picker.
                cell=page.locator('.daycell[data-day="4"][data-start="08:00"]');cell.focus();cell.press('Enter');page.wait_for_selector('#calendar-selection-dialog[open]');f=page.locator('#calendar-selection-form');f.locator('[name="course"]').select_option(second['id']);f.locator('[name="end"]').fill('07:00');f.locator('button[type="submit"]').click();assert 'Ende' in page.locator('#calendar-selection-error').inner_text();page.locator('[data-calendar-cancel]').click();assert page.locator('.event').count()==2
                # Only courses from the selected semester may receive meetings.
                page.locator('#schedule-sem').select_option('2027S');cell=page.locator('.daycell[data-day="0"][data-start="09:00"]');cell.focus();cell.press('Enter');page.wait_for_selector('#calendar-selection-dialog[open]');f=page.locator('#calendar-selection-form');assert f.locator(f'[name="course"] option[value="{first["id"]}"]').count()==0
                f.locator('[name="course"]').evaluate('(select,id)=>{const option=new Option("forged",id);select.add(option);select.value=id;}',first['id']);f.locator('button[type="submit"]').click();assert 'nicht verfügbar' in page.locator('#calendar-selection-error').inner_text();page.keyboard.press('Escape')
                page.reload();page.wait_for_selector('.metric');nav('schedule');page.locator('#schedule-sem').select_option('2026W');assert page.locator('.event').count()==2
                shot('32-selected-calendar-meetings.jpg','.schedule-wrap')
                # Real touch input on a phone-sized viewport uses the same range picker.
                touch=browser.new_page(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,locale='en-GB');touch.on('pageerror',lambda e:errors.append(str(e)));touch.goto(f'http://127.0.0.1:{http.server_port}');touch.wait_for_selector('.metric');touch.locator('#menu-toggle').click();touch.locator('[data-nav="schedule"]').click();touch.locator('#schedule-sem').select_option('2026W')
                cell=touch.locator('.daycell[data-day="0"][data-start="10:00"]');cell.scroll_into_view_if_needed();box=cell.bounding_box();x=box['x']+box['width']/2;y=box['y']+1
                cdp=touch.context.new_cdp_session(touch);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y+134,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                touch.wait_for_selector('#calendar-selection-dialog[open]');assert touch.locator('#calendar-selection-form [name="start"]').input_value()=='10:00';assert touch.locator('#calendar-selection-form [name="end"]').input_value()=='12:00';touch.locator('[data-calendar-cancel]').click()
                # Horizontal touch panning must remain available for later weekdays.
                cell=touch.locator('.daycell[data-day="1"][data-start="10:00"]');cell.scroll_into_view_if_needed();box=cell.bounding_box();x=box['x']+box['width']/2;y=box['y']+30
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':2}]})
                for delta in [30,60,90]:cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x-delta,'y':y,'id':2}]})
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});touch.wait_for_function("()=>document.querySelector('.schedule-wrap').scrollLeft>0");assert touch.locator('#calendar-selection-dialog').count()==0;touch.close()
                assert not errors,errors;print('CONFLICTS/CALENDAR BROWSER PASSED: duplicate and historical source choices, pass rate, encrypted choices/alternatives, new-plan conflict, mark-then-assign, quarter-hours, reverse drag, cancellation, keyboard, invalid times, semester scope, locks, mobile touch and repeated-meeting persistence')
                browser.close()
        finally:http.shutdown();http.server_close();thread.join(timeout=2)

if __name__=='__main__':main()
