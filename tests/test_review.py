import unittest

from review import review_options


ROWS = [
    {'listing_id': 'home-a', 'slot_id': 'one', 'provider': 'demo-a', 'start_at': 300, 'expires_at': 200, 'version': 1},
    {'listing_id': 'home-b', 'slot_id': 'two', 'provider': 'demo-b', 'start_at': 500, 'expires_at': 250, 'version': 1},
]


class ReviewTests(unittest.TestCase):
    def test_exclusions_are_explicit_and_input_order_does_not_change_choices(self):
        result = review_options(ROWS, 100, {'provider': 'demo-b'})
        self.assertEqual([row['slot_id'] for row in result['options']], ['two'])
        self.assertEqual(result['excluded'][0]['reasons'], ['different_provider'])
        self.assertEqual(result, review_options(list(reversed(ROWS)), 100, {'provider': 'demo-b'}))
        self.assertFalse(result['availability_is_confirmation'])

    def test_window_endpoints_are_inclusive_and_limit_is_explained(self):
        self.assertEqual(len(review_options(ROWS, 100, {'start_at': 300, 'end_at': 300})['options']), 1)
        self.assertEqual(review_options(ROWS, 100, {'max_options': 1})['excluded'][0]['reasons'], ['result_limit'])

    def test_invalid_preferences_fail_without_implicit_defaults(self):
        for prefs in ({'max_options': False}, {'provider': ''}, {'start_at': 400, 'end_at': 300},
                      {'approve': True}, {'start_at': None}):
            with self.subTest(prefs=prefs), self.assertRaises(ValueError):
                review_options(ROWS, 100, prefs)
