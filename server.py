"""Loopback API for safe, synthetic tour discovery and human approval."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from core import options
from model import LocalSuggestionAdapter, local_ollama_transport
from store import IntentStore


ROOT = Path(__file__).resolve().parent
SLOTS = json.loads((ROOT / 'slots.json').read_text(encoding='utf-8'))
LOGICAL_NOW = 100


def parse_body(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
    except (UnicodeDecodeError, RecursionError) as error:
        raise ValueError('Invalid JSON encoding or nesting') from error


def make_handler(store, model=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, status, value):
            raw = json.dumps(value, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def local(self):
            return self.headers.get('Host') in {f'localhost:{self.server.server_port}',
                                                f'127.0.0.1:{self.server.server_port}'}

        def do_GET(self):
            if not self.local():
                return self.send_json(403, {'error': 'Nonlocal Host denied'})
            url = urlsplit(self.path)
            if url.path == '/api/health':
                return self.send_json(200, {'status': 'ok', 'mode': 'synthetic-local'})
            if url.path == '/api/options':
                return self.send_json(200, {'options': options(SLOTS, LOGICAL_NOW), 'logical_now': LOGICAL_NOW})
            if url.path in ('/api/status', '/api/events'):
                try:
                    query = parse_qs(url.query, keep_blank_values=True)
                    if set(query) != {'key', 'actor'} or any(len(value) != 1 for value in query.values()):
                        raise ValueError('Expected one key and actor')
                    key, actor = query['key'][0], query['actor'][0]
                    result = store.status(key, actor) if url.path == '/api/status' else store.events(key, actor)
                    return self.send_json(200, result)
                except ValueError as error:
                    return self.send_json(400, {'error': str(error)})
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/style.css': ('style.css', 'text/css')}
            if url.path not in assets:
                return self.send_json(404, {'error': 'Not found'})
            filename, media = assets[url.path]
            raw = (ROOT / 'static' / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', media + '; charset=utf-8')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if not self.local():
                return self.send_json(403, {'error': 'Nonlocal Host denied'})
            if self.headers.get('Origin') and self.headers['Origin'] != 'http://' + self.headers['Host']:
                return self.send_json(403, {'error': 'Cross-origin write denied'})
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                return self.send_json(415, {'error': 'JSON content type required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError('JSON body must be 1-16384 bytes')
                data = parse_body(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object')
                path = urlsplit(self.path).path
                if path == '/api/suggest':
                    if set(data) != {'request'}:
                        raise ValueError('Request text required')
                    available = options(SLOTS, LOGICAL_NOW)
                    result = model.suggest(data['request'], available) if model else {
                        'option': available[0], 'reason': 'Earliest current synthetic option',
                        'authority': 'proposal-only', 'source': 'deterministic'}
                elif path == '/api/propose':
                    if set(data) != {'key', 'actor', 'source', 'listing_id', 'slot_id'}:
                        raise ValueError('Invalid proposal fields')
                    available = options(SLOTS, LOGICAL_NOW, data['listing_id'])
                    selected = next((row for row in available if row['slot_id'] == data['slot_id']), None)
                    if selected is None:
                        raise ValueError('Selected slot is not currently available')
                    result = store.propose(data['key'], data['actor'], data['source'], selected)
                elif path == '/api/approve':
                    if set(data) != {'key', 'actor', 'consent'}:
                        raise ValueError('Invalid approval fields')
                    result = store.approve(data['key'], data['actor'], data['consent'])
                elif path == '/api/provider':
                    if set(data) != {'key', 'outcome', 'receipt'}:
                        raise ValueError('Invalid provider simulation fields')
                    result = store.provider_result(data['key'], data['outcome'], data['receipt'])
                else:
                    return self.send_json(404, {'error': 'Not found'})
                return self.send_json(201, result)
            except (ValueError, TypeError, KeyError) as error:
                return self.send_json(400, {'error': str(error)})
            except OSError:
                return self.send_json(502, {'error': 'Optional local model is unavailable'})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--db', default=str(ROOT / 'intents.sqlite3'))
    parser.add_argument('--model', help='optional local Ollama model name')
    args = parser.parse_args()
    model = LocalSuggestionAdapter(args.model, local_ollama_transport()) if args.model else None
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(IntentStore(args.db), model))
    print(f'Tour Assistant Sandbox: http://127.0.0.1:{server.server_port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
