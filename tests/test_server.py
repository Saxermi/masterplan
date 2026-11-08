import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, VvzCache, initial_state, select_offering, valid_state, build_catalog_query, ELIGIBLE_CORE_PROGRAMMES


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


if __name__ == '__main__':
    unittest.main()
