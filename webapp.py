"""The quiz web app for tonight's walkthroughs.

One tester at a time, not simultaneous Kahoot-style play - that scope cut was
deliberate, made explicit rather than silently assumed, because tonight is
about proving persistent memory works for someone real, not about building a
live multiplayer session under time pressure.

Every answer runs through the REAL pipeline in app/flow.py - the same
extract -> compare -> draft -> check -> (professor review) state machine that
already runs against Mira and Arun. A tester's second wrong answer on the same
concept is compared against their own first one, live, in the same store.

    .venv/bin/python webapp.py
    open http://localhost:8000

Two people, sequentially, are enough to show the second-encounter story:
whoever goes first establishes a first_signal; if they come back and repeat
the same underlying mistake, the demo shows it recognised as recurring, live,
in front of them.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from slice import callback
from slice.config import settings as load_settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import quiz
from app.flow import build_flow
from slice.llm import complete

DB = Path(__file__).parent / "webapp.db"
NOTES = (Path(__file__).parent / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

app = FastAPI()
_store: Store | None = None
_settings = load_settings()
_flow = build_flow(call=complete, notes=NOTES)


def store() -> Store:
    # One process, one store, opened once. FastAPI's dev server is single-
    # worker for this use, so a module-level connection is enough - this is a
    # walkthrough tool for tonight, not a production service.
    global _store
    if _store is None:
        _store = Store(DB)
        try:
            from slice import retrieve
            retrieve.ingest(_store, str(Path(__file__).parent / "corpus"))
        except Exception:
            pass
    return _store


def _page(body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recall</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto;
         padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; }}
  .opt {{ display: block; width: 100%; text-align: left; padding: .9rem 1rem;
          margin: .5rem 0; border: 1px solid #ccc; border-radius: 8px;
          background: #fafafa; font-size: 1rem; cursor: pointer; }}
  .opt:hover {{ background: #eef; }}
  input[type=text] {{ width: 100%; padding: .6rem; font-size: 1rem;
                       margin: .5rem 0; }}
  button.go {{ padding: .7rem 1.4rem; font-size: 1rem; border: none;
               border-radius: 8px; background: #2a5; color: white; }}
  .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 1rem 1.2rem;
           margin: 1rem 0; }}
  .recurring {{ border-color: #d90; background: #fff8ec; }}
  .waiting {{ border-color: #c33; background: #fff0f0; }}
  .tag {{ display: inline-block; font-size: .78rem; padding: .15rem .5rem;
          border-radius: 4px; background: #eee; margin-right: .3rem; }}
  code {{ background: #f0f0f0; padding: .1rem .3rem; border-radius: 3px; }}
</style></head>
<body>{body}</body></html>""")


@app.get("/", response_class=HTMLResponse)
def start():
    return _page("""
<h1>Recall — walkthrough</h1>
<p>Enter the name you want the system to remember you by, then take the quiz.
If you come back later under the same name having repeated a mistake, the
system should notice.</p>
<form action="/begin" method="get">
  <input type="text" name="student" placeholder="your name" required autofocus>
  <button class="go" type="submit">Start</button>
</form>
""")


@app.get("/begin", response_class=HTMLResponse)
def begin(student: str):
    return _quiz_page(student, quiz.QUESTIONS[0].id)


def _quiz_page(student: str, question_id: str) -> HTMLResponse:
    q = quiz.by_id(question_id)
    options = "".join(
        f'<form action="/answer" method="post" style="margin:0">'
        f'<input type="hidden" name="student" value="{student}">'
        f'<input type="hidden" name="question_id" value="{q.id}">'
        f'<input type="hidden" name="chosen" value="{o.key}">'
        f'<button class="opt" type="submit">{o.key}. {o.text}</button>'
        f'</form>'
        for o in q.options
    )
    return _page(f"""
<h1>{q.prompt}</h1>
{options}
""")


@app.post("/answer", response_class=HTMLResponse)
def answer(student: str = Form(...), question_id: str = Form(...),
          chosen: str = Form(...)):
    q = quiz.by_id(question_id)
    attempt = quiz.to_attempt(student, q, chosen)
    attempt["date"] = datetime.date.today().isoformat()

    s = store()
    run_id = s.create_run("recall", meta={"student_id": student})
    s.set_state(run_id, RunState.NEW_ATTEMPT)
    s.append(run_id, "attempt", attempt, produced_by="quiz")
    state = advance(s, run_id, _flow, _settings)

    body = _result_body(s, run_id, state, student, q.id)

    # Next question, if any remain; otherwise offer to start again as someone
    # new, which is also how the same tester demonstrates a second encounter -
    # answering a later question under the same name.
    ids = [x.id for x in quiz.QUESTIONS]
    idx = ids.index(q.id)
    nxt = f'<a class="opt" style="display:inline-block;width:auto" href="/quiz-next?student={student}&after={q.id}">Next question →</a>' \
        if idx + 1 < len(ids) else \
        f'<a class="opt" style="display:inline-block;width:auto" href="/">Done — start over</a>'
    return _page(body + nxt)


@app.get("/quiz-next", response_class=HTMLResponse)
def quiz_next(student: str, after: str):
    ids = [x.id for x in quiz.QUESTIONS]
    idx = ids.index(after)
    return _quiz_page(student, ids[idx + 1])


def _result_body(s: Store, run_id: str, state: RunState, student: str,
                 question_id: str) -> str:
    q = quiz.by_id(question_id)
    attempt = s.latest(run_id, "attempt")
    chosen = q.option(attempt["quiz_meta"]["chosen"])

    parts = [f'<div class="card"><b>{"Correct" if chosen.correct else "Not quite"}.</b> '
             f'{chosen.text}</div>']

    if state is RunState.NEEDS_REVIEW:
        pending = callback.pending(s, run_id)
        q_text = pending[0].question if pending else ""
        parts.append(f"""
<div class="card waiting">
  <span class="tag">waiting on the professor</span>
  <p>{q_text}</p>
  <form action="/review" method="post">
    <input type="hidden" name="run_id" value="{run_id}">
    <input type="hidden" name="question_id" value="{pending[0].id if pending else ''}">
    <button class="opt" name="decision" value="confirm">Confirm — this is a real pattern</button>
    <button class="opt" name="decision" value="reject">Reject — not related</button>
    <button class="opt" name="decision" value="request_more_evidence">Need more evidence</button>
  </form>
</div>""")
        return "".join(parts)

    comparison = s.latest(run_id, "comparison")
    finding = s.latest(run_id, "finding")
    if comparison:
        css = "recurring" if comparison["label"] == "recurring" else ""
        parts.append(f"""
<div class="card {css}">
  <span class="tag">{comparison['label']}</span>
  <p>{comparison['explanation']}</p>
  {'<p><b>Finding:</b> ' + finding['statement'] + '</p>' if finding else ''}
</div>""")
    return "".join(parts)


@app.post("/review", response_class=HTMLResponse)
def review(run_id: str = Form(...), question_id: str = Form(...),
          decision: str = Form(...)):
    s = store()
    callback.answer(s, question_id, decision, who="professor")
    s.set_state(run_id, RunState.RECORD_UPDATED)
    advance(s, run_id, _flow, _settings)

    finding = s.latest(run_id, "finding")
    attempt = s.latest(run_id, "attempt")
    return _page(f"""
<div class="card">
  <span class="tag">recorded</span>
  <p><b>{finding['status']}</b> — {finding['statement']}</p>
</div>
<a class="opt" style="display:inline-block;width:auto" href="/">Back to start</a>
""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
