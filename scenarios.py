"""Replay disclosed synthetic cases offline, with an assertion for every outcome."""
import argparse
import json
from pathlib import Path
import tempfile

from core import options, parse_suggestion
from review import review_options
from store import IntentStore


def evaluate(case):
    data = case['input']
    if case['kind'] == 'discovery':
        rows = options(data['rows'], data['now'], data.get('listing_id'))
        return {'selected': [[row['listing_id'], row['slot_id'], row['version']] for row in rows]}
    if case['kind'] == 'suggestion':
        result = parse_suggestion(data['raw'], options(data['rows'], data['now']))
        return {'selected': [result['option']['listing_id'], result['option']['slot_id']], 'authority': result['authority']}
    if case['kind'] == 'review':
        result = review_options(data['rows'], data['now'], data['preferences'])
        return {'selected': [[row['listing_id'], row['slot_id']] for row in result['options']],
                'excluded': result['excluded'], 'authority': result['authority']}
    if case['kind'] != 'intent':
        raise ValueError('Unknown scenario kind')
    with tempfile.TemporaryDirectory() as folder:
        store = IntentStore(Path(folder) / 'intent.db', lambda: 100)
        calls = {'propose': store.propose, 'approve': store.approve, 'provider': store.provider_result,
                 'cancel': store.cancel_proposal, 'status': store.status}
        observed = []
        for step in data['steps']:
            if step['op'] not in calls:
                raise ValueError('Unknown scenario operation')
            try:
                result = calls[step['op']](*step['args'])
            except ValueError as error:
                if 'error_contains' not in step or step['error_contains'] not in str(error):
                    raise AssertionError('Unexpected intent error: ' + str(error)) from error
                observed.append('rejected')
            else:
                if 'error_contains' in step:
                    raise AssertionError('Expected intent rejection')
                observed.append(result['status'])
        return {'observed': observed,
                'events': [item['status'] for item in store.events(data['key'], data['actor'])]}


def check_case(case):
    if not isinstance(case, dict) or case.get('schema_version') != 1 or case.get('synthetic') is not True:
        raise AssertionError('Expected a disclosed version-1 synthetic fixture')
    try:
        actual = evaluate(case)
    except ValueError as error:
        if 'error_contains' not in case or case['error_contains'] not in str(error):
            raise AssertionError('Unexpected validation error: ' + str(error)) from error
        return
    if 'error_contains' in case:
        raise AssertionError('Expected validation rejection')
    if actual != case['expected']:
        raise AssertionError(f"{case['id']}: expected {case['expected']!r}, received {actual!r}")


def load_cases(directory):
    paths = sorted(Path(directory).glob('*.json'))
    if not 1 <= len(paths) <= 2000:
        raise ValueError('Expected 1-2000 scenario files')
    seen = set()
    for path in paths:
        if path.stat().st_size > 256 * 1024:
            raise ValueError('Scenario exceeds 256 KiB')
        case = json.loads(path.read_text(encoding='utf-8'))
        if case['id'] in seen:
            raise ValueError('Duplicate scenario ID')
        seen.add(case['id'])
        yield path, case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent / 'scenarios')
    args = parser.parse_args()
    count = 0
    try:
        for path, case in load_cases(args.directory):
            try:
                check_case(case)
            except (AssertionError, ValueError, KeyError, TypeError) as error:
                raise ValueError(f'{path.name}: {error}') from error
            count += 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'error: ' + str(error) + '\n')
    print(json.dumps({'passed': count, 'basis': 'generated synthetic regression cases; not historical work'}))


if __name__ == '__main__':
    main()
