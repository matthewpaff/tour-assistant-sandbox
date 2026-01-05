import unittest

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
