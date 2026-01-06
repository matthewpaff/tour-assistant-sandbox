"""Explain deterministic tour preferences without granting booking authority."""
from core import _label, _time, options


def review_options(rows, now, preferences):
    if not isinstance(preferences, dict) or set(preferences) - {
        'listing_id', 'provider', 'start_at', 'end_at', 'max_options'
    }:
        raise ValueError('Unknown tour preference')
    for field in ('listing_id', 'provider'):
        if field in preferences:
            _label(preferences[field], field)
    lower = _time(preferences.get('start_at', now), 'start_at')
    upper = _time(preferences.get('end_at', 4102444800), 'end_at')
    if lower > upper:
        raise ValueError('Tour preference window is reversed')
    limit = preferences.get('max_options', 10)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError('max_options must be 1-50')
    selected, excluded = [], []
    for row in options(rows, now):
        reasons = []
        if 'listing_id' in preferences and row['listing_id'] != preferences['listing_id'].strip():
            reasons.append('different_listing')
        if 'provider' in preferences and row['provider'] != preferences['provider'].strip():
            reasons.append('different_provider')
        if not lower <= row['start_at'] <= upper:
            reasons.append('outside_time_window')
        if not reasons and len(selected) >= limit:
            reasons.append('result_limit')
        if reasons:
            excluded.append({'listing_id': row['listing_id'], 'slot_id': row['slot_id'], 'reasons': reasons})
        else:
            selected.append(row)
    return {'options': selected, 'excluded': excluded, 'authority': 'proposal-only',
            'availability_is_confirmation': False}
