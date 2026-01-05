import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from server import make_handler
from store import IntentStore


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(IntentStore(Path(self.temp.name) / 'intents.db')))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()
        self.temp.cleanup()

    def call(self, path, value=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        body = json.dumps(value).encode() if value is not None and not isinstance(value, bytes) else value
        connection.request('POST' if body is not None else 'GET', path, body,
                           {'Content-Type': 'application/json', **(headers or {})})
        response = connection.getresponse()
        status, raw = response.status, response.read()
        connection.close()
        return status, json.loads(raw)

    def test_assistant_suggestion_cannot_confirm_without_human_consent(self):
        self.assertEqual(self.call('/api/health')[0], 200)
        suggestion = self.call('/api/suggest', {'request': 'Soonest tour'})[1]
        self.assertEqual(suggestion['authority'], 'proposal-only')
        selected = suggestion['option']
        proposed = self.call('/api/propose', {'key': 'request-001', 'actor': 'person-1', 'source': 'assistant',
                       'listing_id': selected['listing_id'], 'slot_id': selected['slot_id']})[1]
        self.assertEqual(proposed['status'], 'PROPOSED')
        self.assertEqual(self.call('/api/provider', {'key': 'request-001', 'outcome': 'confirmed', 'receipt': 'r1'})[0], 400)
        self.assertEqual(self.call('/api/approve', {'key': 'request-001', 'actor': 'person-1', 'consent': True})[1]['status'], 'PENDING_PROVIDER')
        self.assertEqual(self.call('/api/provider', {'key': 'request-001', 'outcome': 'unknown', 'receipt': None})[1]['status'], 'RECONCILING')
        self.assertEqual(self.call('/api/provider', {'key': 'request-001', 'outcome': 'confirmed', 'receipt': 'r1'})[1]['status'], 'CONFIRMED')
        self.assertEqual(len(self.call('/api/events?key=request-001&actor=person-1')[1]), 4)

    def test_host_origin_duplicate_json_and_unavailable_slot(self):
        self.assertEqual(self.call('/api/options', headers={'Host': 'attacker.example'})[0], 403)
        self.assertEqual(self.call('/api/propose', b'{"key":"a","key":"b"}')[0], 400)
        self.assertEqual(self.call('/api/propose', {}, {'Origin': 'https://attacker.example'})[0], 403)
        self.assertEqual(self.call('/api/propose', {'key': 'request-002', 'actor': 'person-1', 'source': 'assistant',
                       'listing_id': 'home-1', 'slot_id': 'missing'})[0], 400)
