"""Inspect synthetic tour options and locally saved intent state."""
import argparse
import json
from pathlib import Path

from core import options
from server import LOGICAL_NOW, SLOTS
from store import IntentStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('options', help='list current synthetic fixture options')
    status = sub.add_parser('status', help='inspect one locally saved intent')
    status.add_argument('key')
    status.add_argument('--actor', required=True)
    status.add_argument('--db', default='intents.sqlite3')
    args = parser.parse_args(argv)
    if args.command == 'options':
        result = {'logical_now': LOGICAL_NOW, 'options': options(SLOTS, LOGICAL_NOW)}
    else:
        if not Path(args.db).is_file():
            parser.error('Intent database does not exist')
        try:
            store = IntentStore(args.db)
            result = {'intent': store.status(args.key, args.actor),
                      'events': store.events(args.key, args.actor)}
        except ValueError as error:
            parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
