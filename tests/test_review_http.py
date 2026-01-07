import json
from http.server import ThreadingHTTPServer
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import make_handler
from store import IntentStore


class ReviewHTTPTests(unittest.TestCase):
    def test_review_and_local_withdrawal_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = IntentStore(Path(folder) / 'state.db', lambda: 100)
            server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(store))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def post(path, data):
                request = Request(f'http://127.0.0.1:{server.server_port}' + path,
                                  json.dumps(data).encode(), {'Content-Type': 'application/json'})
                with urlopen(request, timeout=3) as response:
                    return json.load(response)
            try:
                result = post('/api/review', {'preferences': {'provider': 'sandbox-b'}})
                self.assertEqual([row['slot_id'] for row in result['options']], ['afternoon'])
                self.assertEqual(result['authority'], 'proposal-only')
                post('/api/propose', {'key': 'http-cancel-key', 'actor': 'alice', 'source': 'mobile',
                                     'listing_id': 'home-1', 'slot_id': 'afternoon'})
                with self.assertRaises(HTTPError) as caught:
                    post('/api/cancel-proposal', {'key': 'http-cancel-key', 'actor': 'bob'})
                self.assertEqual(caught.exception.code, 400)
                self.assertEqual(post('/api/cancel-proposal', {'key': 'http-cancel-key', 'actor': 'alice'})['status'], 'CANCELLED')
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)
