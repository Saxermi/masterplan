"""Regression cases for revision handling, real dump schema and semester scopes."""
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from server import (Handler, VvzCache, Store, DEGREES, CATEGORY_PATHS,
                    ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS, select_offering, normalize_meetings)
from vvz_dump import LocalCatalog, _json_value
from vvz_schedule import parse_official_courses
from test_vvz_dump import make_db

FIXTURES = Path(__file__).parent / 'fixtures'
WINDOW = ['2025W', '2026S', '2026W', '2027S']


class CatalogueRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'data.sqlite'
        make_db(self.db)
        self.catalog = LocalCatalog(self.db, DEGREES, CATEGORY_PATHS, ELIGIBLE_CORE_PROGRAMMES, SPECIALISATIONS)

    def tearDown(self):
        self.tmp.cleanup()

    def search(self, programme='cse', category='core', semester='2026W', limit=40, offset=0, specs=(), q=''):
        return self.catalog.search(q, programme, category, specs, semester, WINDOW, limit, offset, select_offering)

    def test_reclassified_course_does_not_match_old_category(self):
        with sqlite3.connect(self.db) as c:
            c.execute('UPDATE unitsectionlink SET section_id=15 WHERE unit_id=111')
        self.assertEqual(self.search()['total'], 0)
        self.assertEqual(self.search(category='case')['total'], 2)

    def test_metadata_and_id_come_from_requested_term(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO learningunit VALUES (113,'401-0000-00L','2027S','Future title','Future title',99,'[]','English','[]')")
            c.execute('INSERT INTO unitsectionlink VALUES (113,11)')
        item = self.search()['results'][0]
        self.assertEqual((item['title'], item['credits'], item['offering']['unit_id']), ('CSE Calculation', 6, 111))
        self.assertNotIn('2027S', item['semesters'])

    def test_programme_root_is_exact_not_geophysics_or_environment(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE sectionpathview SET path_en='Geophysics Master > Core Courses' WHERE id=12")
        self.assertEqual(self.search(programme='physics-msc')['total'], 0)

    def test_specialisations_are_path_segments(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE sectionpathview SET path_en='Computational Science and Engineering Master > Fields of Specialization > Geophysics' WHERE id=11")
        self.assertEqual(self.search(category='specialisation', specs=['Physics'])['total'], 0)
        self.assertEqual(self.search(category='specialisation', specs=['Geophysics'])['total'], 1)
        self.assertEqual(self.search(category='specialisation')['total'], 0)

    def test_recent_window_has_upper_bound_and_pagination(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE learningunit SET semkez='2030W' WHERE id=111")
        self.assertEqual(self.search(semester='recent')['results'][0]['offering']['source_semester'], '2025W')
        first = self.search(programme='all', category='', limit=2)
        second = self.search(programme='all', category='', limit=2, offset=2)
        self.assertTrue(set(x['number'] for x in first['results']).isdisjoint(x['number'] for x in second['results']))

    def test_old_explicit_term_remains_searchable(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE learningunit SET semkez='2023W' WHERE id=112")
        self.assertEqual(self.search(semester='2023W')['results'][0]['offering']['unit_id'], 112)

    def test_indexes_are_installed_on_existing_unindexed_dump(self):
        self.search()
        with sqlite3.connect(self.db) as c:
            indexes = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertIn('mp_link_section_unit', indexes)
        self.assertIn('mp_unit_number_term', indexes)


class ScheduleRegression(unittest.TestCase):
    def test_official_hs26_courses_and_rooms(self):
        ai = normalize_meetings(parse_official_courses((FIXTURES / 'ai-hs26.html').read_text()))
        self.assertEqual([(x['day'], x['start'], x['building'], x['room']) for x in ai],
                         [(3, '10:15', 'HG', '5'), (0, '12:15', 'ML', '44')])
        numerical = normalize_meetings(parse_official_courses((FIXTURES / 'numerical-hs26.html').read_text()))
        self.assertEqual([(x['day'], x['start']) for x in numerical], [(1, '08:15'), (4, '08:15')])

    def test_null_json_collections_and_invalid_clock_times(self):
        self.assertEqual(_json_value('null', []), [])
        self.assertEqual(_json_value('{}', []), [])
        self.assertEqual(normalize_meetings([{'timeslots': [{'weekday': 0, 'start_time': '24:15', 'end_time': '25:00'}]}]), [])
        with self.assertRaises(ValueError):
            parse_official_courses('<html>Upstream error</html>')

    def test_official_schedule_persists_and_is_reused_after_restart(self):
        with tempfile.TemporaryDirectory() as d:
            url = 'https://www.vvz.ethz.ch/Vorlesungsverzeichnis/lerneinheit.view?lerneinheitId=204828&semkez=2026W'
            cache = VvzCache(d)
            response = Mock()
            response.headers = {}
            response.read.return_value = (FIXTURES / 'ai-hs26.html').read_bytes()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            with patch('server.urlopen', return_value=response) as upstream:
                result, source = cache.get(url)
            self.assertEqual(len(result), 2)
            self.assertEqual(source, 'live')
            upstream.assert_called_once()
            restarted = VvzCache(d)
            with patch('server.threading.Thread') as worker:
                saved, status, source = restarted.scheduled(url)
                worker.assert_not_called()
            self.assertEqual((saved, status, source), (result, 'ready', 'cached'))

    def test_failed_requests_retry_after_cooldown(self):
        with tempfile.TemporaryDirectory() as d:
            cache = VvzCache(d)
            cache.failures['url'] = (time.monotonic() - 61, 'temporary outage')
            with patch('server.threading.Thread'):
                self.assertEqual(cache.scheduled('url')[1], 'queued')
                cache.scheduled('url')
            self.assertEqual(cache.pending, ['url'])


class HttpRegression(unittest.TestCase):
    def test_conflicts_missing_catalogue_and_invalid_queries_are_structured(self):
        from http.server import ThreadingHTTPServer
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        import threading
        with tempfile.TemporaryDirectory() as d:
            http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            http.store = Store(d)
            http.catalog = Mock()
            http.catalog.available.return_value = False
            http.vvz = Mock()
            http.vvz_dump = Mock()
            http.vvz_dump.status.return_value = {'available': False, 'phase': 'downloading'}
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{http.server_port}'
            try:
                for suffix, code in [('/api/vvz/search?programme=cse&category=core&semester=2026W', 503),
                                     ('/api/vvz/search?programme=invalid&semester=2026W', 400)]:
                    with self.assertRaises(HTTPError) as error:
                        urlopen(base + suffix, timeout=2)
                    self.assertEqual(error.exception.code, code)
                    self.assertIn('error', json.load(error.exception))
                old = http.store.get()
                http.store.save(old)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + '/api/state', data=json.dumps(old).encode(), headers={'Content-Type': 'application/json'}), timeout=2)
                self.assertEqual(error.exception.code, 409)
                self.assertIn('Revision', json.load(error.exception)['error'])
                http.vvz.get.assert_not_called()
            finally:
                http.shutdown()
                http.server_close()
                thread.join(timeout=2)


class ResponseRegression(unittest.TestCase):
    def test_disconnected_browser_is_not_answered_twice(self):
        for where in ('headers', 'body'):
            handler = object.__new__(Handler)
            handler.send_response = Mock()
            handler.send_header = Mock()
            handler.end_headers = Mock(side_effect=BrokenPipeError() if where == 'headers' else None)
            handler.wfile = Mock()
            if where == 'body':
                handler.wfile.write.side_effect = ConnectionResetError()
            handler.respond(409, {'error': 'Revision conflict'})
            handler.send_response.assert_called_once_with(409)
            self.assertTrue(handler.close_connection)


if __name__ == '__main__':
    unittest.main()
