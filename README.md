# Tour Assistant Sandbox

An original 2026 showcase for safe tour discovery and booking intent review. It models the blueprint's assistant-as-client pattern with synthetic slots and provider outcomes. **No tour is booked, no property is reserved, and no provider is contacted.** Created in November 2026; commits use their actual creation dates.

## Run

Python 3.10+ and the standard library are sufficient. No package installation, account, model download, or external service is required.

```powershell
python server.py
```

Open http://127.0.0.1:8765. The dashboard uses a fixed synthetic logical clock. Select a current slot or request a deterministic suggestion, inspect the proposal, approve it with explicit consent, then simulate an unknown or confirmed provider response. The intent and transition history are saved to a local ignored SQLite database.

An **optional**, separately running local Ollama server can suggest among current read-only options with `python server.py --model MODEL_NAME`. The model response is schema checked and cannot set consent, call booking APIs, or claim confirmation. Tests use a fake transport; no live model inference is required or claimed.

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
python cli.py options
python cli.py status REQUEST_KEY --actor demo-person --db intents.sqlite3
```

## Flow

```mermaid
flowchart LR
  A[Current synthetic slot snapshots] --> B[Read-only options]
  B --> C[Deterministic or local model proposal]
  C --> D[Saved idempotent intent]
  D --> E[Explicit human consent]
  E --> F[Simulated provider result]
  F --> G[Status and audit history]
```

Latest slot versions can revoke a cached option. A proposal records the selected option but has no booking authority. Approval is scoped to the same demo actor and only transitions a proposal once. An uncertain provider result remains `RECONCILING` until an explicit later simulated outcome. The same idempotency key cannot be reused for another actor, source, or slot.

The HTTP service binds to loopback, rejects foreign Host headers and cross-origin writes, and bounds JSON requests. Actor names are demo labels, **not authentication**; this is not a production authorization boundary. Source slots, receipts, and logical times are fixtures. See [HISTORY.md](HISTORY.md) for provenance.
