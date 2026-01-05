import tempfile
import unittest
from pathlib import Path

from store import IntentStore


OPTION = {'listing_id': 'home-1', 'slot_id': 'afternoon', 'provider': 'demo-b'}


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = IntentStore(Path(self.temp.name) / 'intents.db', lambda: 100)

    def tearDown(self):
        self.temp.cleanup()

    def test_human_approval_precedes_provider_confirmation(self):
        key = 'request-001'
        self.assertEqual(self.store.propose(key, 'person-1', 'assistant', OPTION)['status'], 'PROPOSED')
        with self.assertRaises(ValueError):
            self.store.provider_result(key, 'confirmed', 'receipt-1')
        with self.assertRaises(ValueError):
            self.store.approve(key, 'person-1', False)
        self.store.approve(key, 'person-1', True)
        self.assertEqual(self.store.provider_result(key, 'unknown')['status'], 'RECONCILING')
        self.assertEqual(self.store.provider_result(key, 'confirmed', 'receipt-1')['status'], 'CONFIRMED')
        self.assertEqual(len(self.store.events(key, 'person-1')), 4)
        with self.assertRaises(ValueError):
            self.store.status(key, 'other-person')

    def test_idempotency_key_cannot_change_actor_or_slot(self):
        key = 'request-002'
        first = self.store.propose(key, 'person-1', 'web', OPTION)
        self.assertEqual(self.store.propose(key, 'person-1', 'web', OPTION), first)
        with self.assertRaises(ValueError):
            self.store.propose(key, 'person-1', 'web', {**OPTION, 'slot_id': 'morning'})
        with self.assertRaises(ValueError):
            self.store.propose(key, 'person-2', 'web', OPTION)
