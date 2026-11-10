import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, VvzCache, initial_state, select_offering, valid_state, build_catalog_query, ELIGIBLE_CORE_PROGRAMMES, normalize_meetings, migrate_state, recent_semesters


class TestStore(unittest.TestCase):
    def test_initial_state_and_optimistic_revisions(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            first = store.get()
            self.assertEqual(first['revision'], 0)
            first['language'] = 'en'
            saved = store.save(first)
            self.assertEqual(saved['revision'], 1)
            self.assertEqual(store.get()['language'], 'en')
            with self.assertRaises(RuntimeError):
                store.save(first)

    def test_rejects_invalid_data(self):
        s = initial_state()
        s['plans'][0]['courses'].append({'id': 'a', 'semester': '2027S', 'role':'invalid'})
        self.assertFalse(valid_state(s))

    def test_folder_migration(self):
        with tempfile.TemporaryDirectory() as d:
            start = Path(d) / 'source'
            target = Path(d) / 'cloud'
            store = Store(start)
            store.move(str(target))
            self.assertTrue((target / 'masterplan.json').exists())
            self.assertEqual(store.open_folder(str(start)), str(start.resolve()))


class TestCatalog(unittest.TestCase):
    def test_eligible_core_masters_only(self):
        for programme in ELIGIBLE_CORE_PROGRAMMES:
            q = build_catalog_query('numerical', programme, 'eligible-core')
            self.assertIn('o:"core courses"', q)
            self.assertIn('title:"numerical"', q)
        with self.assertRaises(ValueError):
            build_catalog_query('', 'mathematics-bsc', 'eligible-core')
        with self.assertRaises(ValueError):
            build_catalog_query('', 'all', 'eligible-core')

    def test_union_core_course_filter(self):
        q = build_catalog_query('', 'eligible-core-all', 'eligible-core')
        self.assertEqual(q.count('o:"core courses"'), 8)  # MSc (Applied) Mathematics share a VVZ tree
        self.assertIn(' OR ', q)
        self.assertIn('neural systems and computation master', q)
        self.assertIn('electrical engineering and information technology master', q)
        self.assertNotIn('mathematics bachelor', q)
        with self.assertRaises(ValueError):
            build_catalog_query('', 'eligible-core-all', 'elective')

    def test_same_season_proxy_only_past(self):
        semesters={'2025W': 2,'2026S': 3,'2026W': 4}
        self.assertEqual(select_offering(semesters, '2027S'), {'unit_id':3,'source_semester':'2026S','proxy':True})
        self.assertEqual(select_offering(semesters, '2026W'), {'unit_id':4,'source_semester':'2026W','proxy':False})
        self.assertIsNone(select_offering(semesters,'2024S')['unit_id'])


class TestMeetingIntegration(unittest.TestCase):
    def test_normalize_vvz_timetable_with_real_fields(self):
        raw = [{"number":"401-5555-00L","title":"Demo course","timeslots":[
            {"weekday":0,"start_time":"08:15","end_time":"10:00","building":"HG","floor":"F","room":"1","date":None,"biweekly":True,"first_half_semester":False,"second_half_semester":False},
            {"weekday":5,"start_time":None,"end_time":None},
            {"weekday":8,"start_time":"12:15","end_time":"14:00"}]}]
        result = normalize_meetings(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['start'], '08:15')
        self.assertEqual(result[0]['building'], 'HG')
        self.assertTrue(result[0]['biweekly'])
        self.assertEqual(len(result[0]['slotKey']),20)
        self.assertEqual(result, normalize_meetings(raw))

    def test_empty_and_bad_data(self):
        self.assertEqual(normalize_meetings([]), [])
        with self.assertRaises(ValueError):
            normalize_meetings({'something':'bad'})

    def test_queue_does_not_make_second_upstream_call(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            cache=VvzCache(d)
            url='https://vvzapi.ch/api/v1/course/get/123'
            with patch('server.threading.Thread') as thread:
                payload,status,source=cache.scheduled(url)
                self.assertEqual((status,source),('queued','pending'))
                cache.scheduled(url)
                self.assertEqual(cache.pending,[url])
                self.assertEqual(thread.call_count,1)

    def test_programme_scope_uses_master_section(self):
        self.assertIn('o:"computational science and engineering master"',build_catalog_query('', 'cse','core'))
        self.assertIn('number:"401-3663-00L"',build_catalog_query('401-3663-00L','cse','core'))
        self.assertIn('o:"computational science and engineering bachelor"',build_catalog_query('', 'cse-bsc','requirement'))

    def test_scenario_migration_keeps_old_plans(self):
        previous=initial_state()
        previous.pop('actualPlan');previous.pop('interests');previous.pop('scientificWorksBSc')
        previous['schema']=1
        previous['plans'][0]['courses']=[{'id':'old','semester':'2026W','role':'core','title':'Previously saved'}]
        migrated=migrate_state(previous)
        self.assertTrue(valid_state(migrated))
        self.assertEqual(migrated['plans'][0]['courses'][0]['title'],'Previously saved')
        self.assertEqual(migrated['activePlan'],'actual')

    def test_recent_semester_window(self):
        from datetime import datetime
        self.assertEqual(recent_semesters(datetime(2026,11,8)),['2025W','2026S','2026W','2027S','2027W'])


if __name__ == '__main__':
    unittest.main()
