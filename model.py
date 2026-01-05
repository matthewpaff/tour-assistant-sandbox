"""Optional local model boundary; responses can only suggest validated options."""
import json
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from core import _label, parse_suggestion


class LocalSuggestionAdapter:
    def __init__(self, model, transport):
        self.model = _label(model, 'model name', 100)
        self.transport = transport

    def suggest(self, request_text, available):
        request_text = _label(request_text, 'request', 1000)
        minimal = [{'listing_id': row['listing_id'], 'slot_id': row['slot_id'],
                    'start_at': row['start_at']} for row in available]
        payload = {'model': self.model, 'stream': False, 'format': 'json',
                   'messages': [{'role': 'system', 'content': 'Choose one listed tour option. Return JSON with listing_id, slot_id, reason. Do not book or claim confirmation.'},
                                {'role': 'user', 'content': json.dumps({'request': request_text, 'options': minimal})}]}
        reply = self.transport(payload)
        if not isinstance(reply, dict) or not isinstance(reply.get('message'), dict):
            raise ValueError('Invalid local model response')
        return parse_suggestion(reply['message'].get('content'), available)


def local_ollama_transport(url='http://127.0.0.1:11434/api/chat'):
    parts = urlsplit(url)
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or parts.path != '/api/chat' or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('Only a local Ollama chat endpoint is supported')
    def send(payload):
        raw = json.dumps(payload).encode('utf-8')
        request = Request(url, data=raw, headers={'Content-Type': 'application/json'})
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                raise ValueError('Local model redirects are not followed')
        with build_opener(NoRedirect).open(request, timeout=5) as response:
            body = response.read(65537)
        if len(body) > 65536:
            raise ValueError('Local model response is too large')
        return json.loads(body)
    return send
