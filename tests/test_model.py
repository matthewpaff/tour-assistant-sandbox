import unittest
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from core import options
from model import LocalSuggestionAdapter, local_ollama_transport


class ModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.available = options([{'listing_id': 'home-1', 'slot_id': 'one', 'provider': 'demo',
                                   'start_at': 300, 'expires_at': 200, 'version': 1}], 100)

    def test_model_receives_only_read_only_options_and_returns_proposal(self):
        sent = []
        def fake(payload):
            sent.append(payload)
            return {'message': {'content': '{"listing_id":"home-1","slot_id":"one","reason":"Fits"}'}}
        result = LocalSuggestionAdapter('demo-model', fake).suggest('Find a time', self.available)
        self.assertEqual(result['authority'], 'proposal-only')
        self.assertNotIn('provider', sent[0]['messages'][1]['content'])
        self.assertNotIn('consent', sent[0]['messages'][1]['content'])
        self.assertFalse(sent[0]['stream'])

    def test_external_endpoints_and_model_booking_claims_are_rejected(self):
        with self.assertRaises(ValueError):
            local_ollama_transport('https://model.example/api/chat')
        adapter = LocalSuggestionAdapter('demo', lambda _: {'message': {'content':
            '{"listing_id":"home-1","slot_id":"one","reason":"Booked","confirmed":true}'}})
        with self.assertRaises(ValueError):
            adapter.suggest('Book it', self.available)

    def test_local_http_model_wire_is_only_a_suggestion(self):
        received = []
        class FakeModel(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                body = json.dumps({'message': {'content':
                    '{"listing_id":"home-1","slot_id":"one","reason":"Fixture match"}'}}).encode()
                self.send_response(200);self.send_header('Content-Length', str(len(body)))
                self.end_headers();self.wfile.write(body)
        server = HTTPServer(('127.0.0.1', 0), FakeModel)
        worker = threading.Thread(target=server.serve_forever, daemon=True);worker.start()
        try:
            transport = local_ollama_transport(f'http://127.0.0.1:{server.server_port}/api/chat')
            suggestion = LocalSuggestionAdapter('fixture-model', transport).suggest('Soonest', self.available)
            self.assertEqual(suggestion['authority'], 'proposal-only')
            self.assertEqual(received[0]['model'], 'fixture-model')
            self.assertFalse(received[0]['stream'])
        finally:
            server.shutdown();worker.join();server.server_close()
