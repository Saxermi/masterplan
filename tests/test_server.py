import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, VvzCache, initial_state, select_offering, valid_state


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
    def test_same_season_proxy_only_past(self):
        semesters={'2025W': 2,'2026S': 3,'2026W': 4}
        self.assertEqual(select_offering(semesters, '2027S'), {'unit_id':3,'source_semester':'2026S','proxy':True})
        self.assertEqual(select_offering(semesters, '2026W'), {'unit_id':4,'source_semester':'2026W','proxy':False})
        self.assertIsNone(select_offering(semesters,'2024S')['unit_id'])


if __name__ == '__main__':
    unittest.main()
