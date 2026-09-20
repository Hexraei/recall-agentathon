# RUN.md — the demo command

**The demo URL (what judges open):**

> https://stranger-spender-duckling.ngrok-free.dev

This single URL serves everything: student quiz, professor review, personal
report, teacher dashboard, and the persistent-memory demo. It is a live ngrok
tunnel to the real server.

**Where the server runs — Hexraei's laptop, already set up and running.** The
ngrok tunnel requires the ngrok dependencies and an ngrok API key, so the
server (`webapp.py`) plus the tunnel are running on Hexraei's machine with all
required variables exported there. Judges need only a browser at the URL above
— nothing to install, nothing to run locally. If the tunnel is down, restart
it on Hexraei's laptop (`ngrok http 8000`, with the team's ngrok auth token
exported). The teacher database lives on that laptop, so the dashboard is
previewed from our own machines, not exposed to the public URL.

---

## Running it anywhere (Windows included)

No Bash required anywhere: `test.sh` is a convenience, not a requirement.

### The one-time setup (per machine)

```bat
copy .env.example .env
notepad .env
```

Set **GROQ_API_KEY** (free at console.groq.com). Leave `TYPSAFE_JEV_MODEL`
**empty/unset** — the checker runs fully code-based and needs no second key.
That is the whole configuration.

**Working key for judges, so nobody has to sign up mid-demo:**

```
GROQ_API_KEY=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
```

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

(Not a hand-picked list of packages — `requirements.txt` also has `fastapi`,
`sqlite-vec`, `fastembed`, and `python-multipart`, all of which the app
genuinely imports at startup. Verified directly: installing just
`pydantic httpx uvicorn pytest` in a clean venv fails immediately on
`import webapp` with `ModuleNotFoundError: No module named 'fastapi'`.)

### The web app — quiz and personal review

```bat
.venv\Scripts\python webapp.py
```

Open **http://localhost:8000**. A student signs up, answers twenty questions,
and their **personal review generates on the spot** when the last answer
lands — one model draft, then three deterministic code checks
(citations → distinct-evidence → claim-strength) → report shown. Decide the
database before starting (see below); two servers on one file is a fork, not
a backup.

```bat
set RECALL_DB=webapp.db                 :: real tester data (default)
.venv\Scripts\python webapp.py
```

Teacher view: same base URL, dashboard link. For a rehearsal with the
simulated cohort:

```bat
set RECALL_DB=demo.db
.venv\Scripts\python webapp.py
```

### The terminal story (pipeline itself, no browser)

```bat
.venv\Scripts\python live.py --full
```

Two encounters: the first finds nothing to compare; the second reads the
first one's committed records, flags the pattern, and **suspends waiting for
the professor** — the step that sends work backwards. Answer it from a second
terminal to watch it resume to `confirmed_recurring` (state survived the
process boundary — that IS the persistent-memory claim):

```bat
.venv\Scripts\python -c "import sys; sys.path.insert(0,'.'); from slice.config import settings as load_settings; from slice.store import Store; from slice.records import RunState; from slice.runner import advance; from slice import callback; from app.flow import build_flow; s=Store('live.db'); rid=[r['id'] for r in s.db.execute(\"SELECT id FROM runs WHERE domain='recall' ORDER BY created_at DESC LIMIT 1\")][0]; p=callback.pending(s, rid)[0]; callback.answer(s, p.id, 'confirm', who='professor'); s.set_state(rid, RunState.RECORD_UPDATED); advance(s, rid, build_flow(notes=open('corpus/ds-notes.md').read()), load_settings()); print('final:', (s.latest(rid,'summary') or {}).get('status'))"
```

(Verified by actually running it end to end: `advance()` requires a
`settings` argument the original command never passed, which raised
`TypeError: advance() missing 1 required positional argument: 'settings'`
before this fix. With `load_settings()` added and passed through, it prints
`final: confirmed_recurring`, exactly as the surrounding text says.)

### Optional sanity check before judges

```bat
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.venv\Scripts\python -m pytest tests -q
```

Stubbed no-network fallback (architecture only, no key, no wifi needed):
`.venv\Scripts\python demo.py`.

**No Jev anywhere.** Every judge-facing verb works with one Groq key: the
compare step's verdict and the report check both run through the
deterministic code checks, whose rejections and back-edges are the demo.
`TYPSAFE_JEV_MODEL` stays unset, so the Jev transport never engages.
