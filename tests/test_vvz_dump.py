"""Offline VVZ integration tests; entirely synthetic SQLite and ZIP data."""
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS, VvzCache, UpstreamRateLimit, recent_semesters, select_offering, normalize_meetings
from vvz_dump import LocalCatalog, VvzDump, install_zip, validate_db


def make_db(file):
    con=sqlite3.connect(file)
    con.executescript('''
        CREATE TABLE learningunit (id INTEGER PRIMARY KEY, number TEXT, semkez TEXT, title TEXT, title_english TEXT, credits REAL, levels TEXT, language TEXT, groups TEXT);
        CREATE TABLE course (number TEXT, semkez TEXT, unit_id INTEGER, title TEXT, timeslots TEXT);
        CREATE TABLE unitsectionlink (unit_id INTEGER, section_id INTEGER);
        CREATE TABLE sectionpathview (id INTEGER, path_en TEXT, path_de TEXT);
        CREATE TABLE rating (course_number TEXT, recommended REAL, engaging REAL, difficulty REAL, effort REAL, resources REAL);
        INSERT INTO sectionpathview VALUES (11,'Computational Science and Engineering Master > Core Courses','CSE Master > Kernfächer');
        INSERT INTO sectionpathview VALUES (12,'Physics Master > Core Courses','Physik Master > Kernfächer');
        INSERT INTO sectionpathview VALUES (13,'Mathematics Master > Electives','Mathematik Master > Wahlfächer');
        INSERT INTO sectionpathview VALUES (14,'Mathematics Bachelor > Core Courses','Mathematik Bachelor > Kernfächer');
        INSERT INTO sectionpathview VALUES (15,'Computational Science and Engineering Master > Case Studies','CSE Master > Fallstudien');
    ''')
    courses=[
        (111,'401-0000-00L','2026W','CSE Calculation', 6,11),
        (112,'401-0000-00L','2025W','CSE Calculation Old', 6,11),
        (201,'402-0000-00L','2026S','Physics Methods', 4,12),
        (301,'403-0000-00L','2026W','Pure Math Elective', 5,13),
        (401,'404-0000-00L','2026W','Bachelor Methods', 6,14),
        (501,'405-0000-00L','2026W','CSE Case Study I', 3,15),
    ]
    for id_,number,sem,title,credits,section in courses:
        con.execute('INSERT INTO learningunit VALUES (?,?,?,?,?,?,?,?,?)',(id_,number,sem,title,title,credits,'["MSC"]','English',json.dumps([{'name':'Exercise 1','timeslots':[{'weekday':1,'start_time':'13:15','end_time':'15:00','building':'HG','floor':'F','room':'2'}]}])))
        con.execute('INSERT INTO unitsectionlink VALUES (?,?)',(id_,section))
    con.execute('INSERT INTO rating VALUES (?,?,?,?,?,?)',('401-0000-00L',4,5,4,5,4))
    con.execute('INSERT INTO course VALUES (?,?,?,?,?)',('401-0000-00L','2026W',111,'Demo Lecture',json.dumps([{'weekday':0,'start_time':'08:15','end_time':'10:00','building':'HG','floor':'F','room':'1','date':None,'biweekly':False,'first_half_semester':False,'second_half_semester':False}])))
    con.commit()
    con.close()


def create_zip(sqlite_path,zip_path):
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as f:
        f.write(sqlite_path,'export/database.sqlite')


class FakeUpstream:
    def __init__(self,archive):
        self.archive=Path(archive)
        self.metadata_calls=0
        self.download_calls=0
        self.last_modified=100
        self.fail=False

    def get(self,url,wait=False,force=False):
        self.metadata_calls+=1
        return {'size_in_bytes':self.archive.stat().st_size,'last_modified_ms':self.last_modified},'live'

    def download(self,url,target,max_bytes):
        self.download_calls+=1
        if self.fail:
            Path(target).write_bytes(b'not really a ZIP')
        else:
            shutil.copyfile(self.archive,target)


class TestVvzDump(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=self.root/'source.sqlite'
        self.zip=self.root/'data.zip'
        make_db(self.db)
        create_zip(self.db,self.zip)
        self.local=self.root/'cache'/'database.sqlite'
        self.catalog=LocalCatalog(self.local,DEGREES,CATEGORY_PATHS,ELIGIBLE_CORE_PROGRAMMES,SPECIALISATIONS)

    def tearDown(self):
        self.tmp.cleanup()

    def test_download_sqlite_then_local_search_and_timetable(self):
        upstream=FakeUpstream(self.zip)
        dump=VvzDump(self.local.parent,upstream,self.catalog)
        dump._refresh()
        self.assertEqual(dump.status()['phase'],'ready')
        self.assertEqual(upstream.download_calls,1)
        self.assertTrue(validate_db(self.local))
        window=['2025W','2026S','2026W','2027S']
        x=self.catalog.search('', 'cse','core',[], '2026W',window,50,0,select_offering)
        self.assertEqual(x['total'],1)
        self.assertEqual(x['source'],'local-dump')
        self.assertEqual(x['results'][0]['rating'],4.4)
        self.assertEqual(x['results'][0]['offering']['unit_id'],111)
        self.assertEqual(self.catalog.unit(111)['groups'][0]['name'],'Exercise 1')
        self.assertEqual(normalize_meetings(self.catalog.meetings(111))[0]['building'],'HG')
        selected=self.catalog.search('Physics', 'physics-msc','eligible-core',[], '2026S',window,50,0,select_offering)
        self.assertEqual(selected['total'],1)
        self.assertEqual(selected['total'],1)
        self.assertFalse(selected['results'][0]['offering']['proxy'])
        self.assertEqual(selected['results'][0]['offering']['source_semester'],'2026S')
        with self.assertRaises(ValueError):
            self.catalog.search('', 'mathematics-bsc','eligible-core',[], 'recent',window,10,0,select_offering)
        self.assertTrue(self.catalog.search('', 'cse','core',[], '2027S',window,50,0,select_offering)['results'][0]['offering']['seasonMismatch'])
        case=self.catalog.search('','cse','case',[],'2026W',window,20,0,select_offering)
        self.assertEqual(case['results'][0]['number'],'405-0000-00L')

    def test_unchanged_dump_is_not_redownloaded_and_persists_after_restart(self):
        upstream=FakeUpstream(self.zip)
        dump=VvzDump(self.local.parent,upstream,self.catalog)
        dump._refresh()
        dump._refresh()
        self.assertEqual((upstream.metadata_calls,upstream.download_calls),(2,1))
        again=VvzDump(self.local.parent,upstream,self.catalog)
        self.assertTrue(again.status()['available'])
        self.assertGreater(again.status()['lastChecked'],0)
        with patch('vvz_dump.threading.Thread') as worker:
            again.check()
            self.assertEqual(worker.call_count,0)  # 24h cache survives restart

    def test_changed_metadata_downloads_and_corrupt_zip_keeps_old_db(self):
        up=FakeUpstream(self.zip)
        dump=VvzDump(self.local.parent,up,self.catalog)
        dump._refresh()
        before=self.local.read_bytes()
        up.last_modified+=1
        up.fail=True
        dump._refresh()
        self.assertEqual(up.download_calls,2)
        self.assertEqual(dump.status()['phase'],'stale')
        self.assertEqual(self.local.read_bytes(),before)
        self.assertEqual(self.catalog.search('','cse','core',[],'2026W',['2025W','2026S','2026W','2027S'],5,0,select_offering)['total'],1)

    def test_local_http_routes_do_not_call_upstream_after_dump_install(self):
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen as real_urlopen
        from unittest.mock import Mock
        from server import Handler, Store
        up=FakeUpstream(self.zip)
        dump=VvzDump(self.local.parent,up,self.catalog)
        dump._refresh()
        live=Mock()
        live.get.side_effect=AssertionError('No per-course VVZ request should happen offline')
        live.scheduled.side_effect=AssertionError('No timetable VVZ request should happen offline')
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        http.store=Store(self.root/'user-data')
        http.vvz=live
        http.vvz_dump=dump
        http.catalog=self.catalog
        thread=threading.Thread(target=http.serve_forever,daemon=True)
        thread.start()
        address=f'http://127.0.0.1:{http.server_port}'
        def fetch(path):
            with real_urlopen(address+path,timeout=3) as response:
                return json.load(response)
        try:
            status=fetch('/api/vvz/dump/status')
            self.assertTrue(status['available'])
            self.assertEqual(status['maxRequestsPerMinute'],1)
            query=fetch('/api/vvz/search?programme=cse&category=core&semester=2026W')
            self.assertEqual(query['source'],'local-dump')
            self.assertEqual(query['results'][0]['number'],'401-0000-00L')
            unit=fetch('/api/vvz/unit/111')
            self.assertEqual(unit['source'],'local-dump')
            self.assertEqual(unit['unit']['number'],'401-0000-00L')
            times=fetch('/api/vvz/times/111')
            self.assertEqual(times['source'],'local-dump')
            self.assertEqual(times['status'],'ready')
            self.assertEqual(times['groupStatus'],'ready')
            self.assertEqual(len(times['meetings']),2)
            self.assertEqual(up.metadata_calls,1)
            self.assertEqual(up.download_calls,1)
            live.get.assert_not_called()
            live.scheduled.assert_not_called()
        finally:
            http.shutdown()
            http.server_close()
            thread.join(timeout=2)

    def test_zip_bomb_and_missing_schema_are_rejected(self):
        bad=self.root/'bad.zip'
        with zipfile.ZipFile(bad,'w') as f:
            f.writestr('bad.zip','not a sqlite database')
        with self.assertRaises(ValueError):
            install_zip(bad,self.local)
        broken=self.root/'broken.sqlite'
        sqlite3.connect(broken).close()
        create_zip(broken,bad)
        with self.assertRaises(ValueError):
            install_zip(bad,self.local)

    def test_rate_is_one_request_per_minute_shared_by_api_and_dump(self):
        # GitHub runners can have a monotonic uptime below 60 seconds.
        with patch('server.time.monotonic',return_value=0):
            fresh=UpstreamRateLimit(interval=60)
            fresh.acquire()  # first call must never be delayed
            with self.assertRaises(RuntimeError):
                fresh.acquire()
        gate=UpstreamRateLimit(interval=60)
        gate.acquire()
        with self.assertRaisesRegex(RuntimeError,'VVZ rate limit'):
            gate.acquire()
        # Simulate the same gate being used by a normal endpoint and dump client.
        gate.last_request-=60.01
        gate.acquire()
        with self.assertRaises(RuntimeError):
            gate.acquire()


if __name__=='__main__':
    unittest.main()
