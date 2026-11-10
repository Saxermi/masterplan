import sqlite3
import tempfile
from pathlib import Path
import unittest
from server import LocalCatalog, DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS, select_offering, Store, initial_state
from test_vvz_dump import make_db

class SemesterFlow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'catalog.sqlite';make_db(self.db)
        self.catalog=LocalCatalog(self.db,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS)
    def tearDown(self):self.tmp.cleanup()
    def search(self,term,category='core',programme='cse'):
        return self.catalog.search('',programme,category,[],term,['2025W','2026S','2026W','2027S','2027W'],40,0,select_offering)
    def test_only_exact_offerings_no_historical_proxy(self):
        self.assertEqual(self.search('2027W')['total'],0)
        self.assertEqual(self.search('2027S')['total'],0)
        self.assertEqual(self.search('2026W')['results'][0]['offering']['unit_id'],111)
    def test_two_concrete_semesters_include_both_offerings(self):
        result=self.search('2026S,2026W','','all')
        self.assertEqual(result['total'],5)
        self.assertTrue(all(set(c['semesters'])<= {'2026W','2026S'} for c in result['results']))
    def test_core_programme_provenance(self):
        result=self.search('2026S','eligible-core','eligible-core-all')
        self.assertEqual(result['results'][0]['coreProgrammes'],['physics master'])
    def test_sip_uses_global_section_and_scientific_uses_known_units(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO sectionpathview VALUES (30,'Science in Perspective > Type A','')")
            for uid,number,title in [(801,'851-9999-00L','Science example'),(802,'401-2000-00L','Scientific Works in Mathematics'),(803,'402-2000-00L','Scientific Works in Physics')]:
                c.execute('INSERT INTO learningunit VALUES (?,?,?,?,?,?,?,?,?)',(uid,number,'2026W',title,title,2,'[]','English','[]'))
            c.execute('INSERT INTO unitsectionlink VALUES (801,30)')
        self.assertEqual(self.search('2026W','sip')['total'],1)
        self.assertEqual(self.search('2026W','scientific')['total'],2)
    def test_new_wrong_term_allocations_are_rejected_by_store(self):
        store=Store(Path(self.tmp.name)/'personal');s=store.get()
        s['actualPlan']['courses']=[dict(id='bad',number='401-0000-00L',title='Wrong term',role='core',status='planned',ects=6,semester='2027S',unitId=111,sourceSemester='2026W',events=[])]
        with self.assertRaisesRegex(ValueError,'not offered'):store.save(s)
        self.assertEqual(store.get()['revision'],0)
