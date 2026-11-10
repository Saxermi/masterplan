"""Validate API input independently of academic draft completeness."""
import copy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import Handler, Store, initial_state, valid_state


def course(**changes):
    return dict(id='course-1', number='401-0001-00L', title='Synthetic module', semester='2026W',
                role='core', status='planned', ects=6, events=[], **changes)


def document():
    state=initial_state()
    state['actualPlan']['courses']=[course()]
    return state


class TestAllocationStorage(unittest.TestCase):
    def test_incomplete_plans_and_more_than_130_credits_remain_saveable(self):
        for ects in [0,6,40]:
            with self.subTest(ects=ects):
                s=document()
                s['actualPlan']['courses']=[dict(course(),id=f'c{i}',number=f'TEST-{i}',ects=ects) for i in range(10)]
                self.assertTrue(valid_state(s))
        self.assertTrue(valid_state(initial_state()))

    def test_invalid_ects_status_category_and_types(self):
        invalid={
            'ects':[-1,41,True,False,'6',None,float('nan'),float('inf'),{},[]],
            'status':['failed','done','',None,[],{}],
            'role':['eligible-core','unknown','',None,[],{}],
            'semester':['HS26','2026X','',None,[],{}],
            'id':['',None,[],{}],
            'title':[None,[],{},'x'*251],
            'number':[None,{},[],'x'*61],
            'events':[None,{},'invalid'],
            'subtype':['lab',[],{}],
            'creditApproved':[0,1,'true',[],{}],
            'usedForBSc':[0,1,None,'false'],
            'locked':[0,'false',None],
            'unitId':['123',0,-1,True,{},[]],
            'sourceSemester':['HS26',{},[]],
        }
        for field,values in invalid.items():
            for value in values:
                with self.subTest(field=field,value=value):
                    s=document();s['actualPlan']['courses'][0][field]=value
                    self.assertFalse(valid_state(s))

    def test_invalid_root_shapes_are_rejected_without_exceptions(self):
        for value in [None, [], '', 1, True, {}]:
            self.assertFalse(valid_state(value))
        for key, values in {'schema':[None,1,3], 'revision':[-1,True,1.5,None],
                            'plans':[None,{},'bad'], 'history':[None,{}], 'interests':[None,{}],
                            'selectedSpecialisations':[None,{}], 'actualPlan':[None,[],{}],
                            'activePlan':[None,{},[]]}.items():
            for value in values:
                with self.subTest(key=key,value=value):
                    s=document();s[key]=value;self.assertFalse(valid_state(s))
        s=document();del s['actualPlan']['courses'][0]['events'];self.assertFalse(valid_state(s))

    def test_invalid_events(self):
        base={'day':0,'start':'08:15','end':'10:00'}
        for field,values in {'day':[-1,7,True,'0',None], 'start':['24:00','9:00','12:00',None,{}],
                             'end':['08:15','07:00','25:00',None], 'date':['2026-02-30',True,{},'wrong'],
                             'biweekly':['true',0], 'room':[{},'x'*101]}.items():
            for value in values:
                with self.subTest(field=field,value=value):
                    s=document();s['actualPlan']['courses'][0]['events']=[dict(base,**{field:value})]
                    self.assertFalse(valid_state(s))

    def test_plan_membership_locks_and_unique_record_ids(self):
        for mutate in [lambda s:s['actualPlan'].update(id='not-actual'),
                       lambda s:s['actualPlan'].update(semesters=['2026W','2026W']),
                       lambda s:s['actualPlan'].update(lockedSemesters=['2024W']),
                       lambda s:s['actualPlan']['courses'][0].update(semester='2024W'),
                       lambda s:s['actualPlan']['courses'].append(copy.deepcopy(s['actualPlan']['courses'][0])),
                       lambda s:s.update(activePlan='missing'),
                       lambda s:s['plans'].append(copy.deepcopy(s['plans'][0]))]:
            s=document();mutate(s);self.assertFalse(valid_state(s))

    def test_malformed_history_shortlist_and_specialisation_metadata(self):
        for key,values in {'history':[[None],[{}],[course()]],'selectedSpecialisations':[['Physics','Physics'],['Unknown'],[{}]],
                           'interests':[[{'id':'interest','title':'Test','offerings':[]}],
                                        [{'id':'interest','title':'Test','offerings':{'HS26':123}}],
                                        [{'id':'interest','title':'Test','offerings':{'2026W':'123'}}],
                                        [{'id':'interest','title':'Test','ects':-1}]],'scientificWorksBSc':['yes',1,None]}.items():
            for value in values:
                with self.subTest(key=key,value=value):
                    s=document();s[key]=value;self.assertFalse(valid_state(s))

    def test_grades_cannot_leak_through_nested_imports(self):
        for key in ['grade','gradeValue','noteValue']:
            s=document();s['actualPlan']['courses'][0]['events']=[{'day':0,'start':'08:00','end':'10:00','metadata':{key:5.5}}]
            self.assertFalse(valid_state(s))

    def test_case_studies_can_repeat_by_number_in_different_semesters(self):
        s=document();s['actualPlan']['courses']=[dict(course(),role='case',ects=3),dict(course(),id='case-2',role='case',ects=3,semester='2027S')]
        self.assertTrue(valid_state(s))

    def test_invalid_save_never_changes_persisted_data(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);before=store.get();bad=document();bad['actualPlan']['courses'][0]['ects']=-1
            with self.assertRaises(ValueError):store.save(bad)
            self.assertEqual(store.get(),before)

    def test_invalid_state_and_import_http_requests_leave_state_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.store=Store(d)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            try:
                before=http.store.get()
                for path in ['/api/state','/api/import']:
                    for field,value in [('ects',-1),('semester','HS26'),('events',None),('status','fake')]:
                        with self.subTest(path=path,field=field):
                            bad=document();bad['actualPlan']['courses'][0][field]=value
                            req=Request(f'http://127.0.0.1:{http.server_port}{path}',data=json.dumps(bad).encode(),headers={'Content-Type':'application/json'})
                            with self.assertRaises(HTTPError) as error:urlopen(req,timeout=3)
                            self.assertEqual(error.exception.code,400);self.assertIn('error',json.load(error.exception));self.assertEqual(http.store.get(),before)
            finally:
                http.shutdown();http.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
