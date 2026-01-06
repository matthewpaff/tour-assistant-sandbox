import tempfile
import unittest
from pathlib import Path

from store import IntentStore


class RecoveryTests(unittest.TestCase):
    def test_only_owner_can_withdraw_before_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            store = IntentStore(Path(folder) / 'state.db', lambda: 100)
            store.propose('cancel-key', 'alice', 'mobile', {'listing_id': 'a', 'slot_id': 'b', 'provider': 'c'})
            with self.assertRaises(ValueError):
                store.cancel_proposal('cancel-key', 'bob')
            self.assertEqual(store.cancel_proposal('cancel-key', 'alice')['status'], 'CANCELLED')
            with self.assertRaises(ValueError):
                store.approve('cancel-key', 'alice', True)
            self.assertEqual(len(store.events('cancel-key', 'alice')), 2)

    def test_terminal_provider_replay_is_idempotent_but_conflicts_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = IntentStore(Path(folder) / 'state.db', lambda: 100)
            store.propose('confirm-key', 'alice', 'web', {'listing_id': 'a', 'slot_id': 'b', 'provider': 'c'})
            store.approve('confirm-key', 'alice', True)
            with self.assertRaises(ValueError):
                store.cancel_proposal('confirm-key', 'alice')
            first = store.provider_result('confirm-key', 'confirmed', 'receipt-a')
            self.assertEqual(store.provider_result('confirm-key', 'confirmed', 'receipt-a'), first)
            with self.assertRaises(ValueError):
                store.provider_result('confirm-key', 'confirmed', 'receipt-b')
            self.assertEqual(len(store.events('confirm-key', 'alice')), 3)
