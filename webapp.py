"""The quiz web app: student signup, a 20-question run, and a teacher dashboard.

Shape of the thing
------------------
    /                signup - name, phone, register number, department
    /quiz/{sid}      one question at a time, no feedback, progress bar
    /answer          POST, writes a row, redirects to the next question
    /report/{sid}    the consolidated agent report, after question 20
    /teacher         pick a department
    /teacher/{dept}  class report + per-student list, both agent-written
    /teacher/{dept}/{sid}  one student, seen by the teacher

Why there is no feedback per question
-------------------------------------
Deliberate, and load-bearing. A student told they got Q3 wrong answers Q4
differently, and the twenty answers stop being twenty independent observations
of what they know. It also keeps the model out of the quiz loop entirely - the
answer path is one SQL insert, so it stays instant under a room full of people
and never touches a rate limit. All the model work happens once, at the end,
in app/report.py.

Run it:
    .venv/bin/python webapp.py
    open http://localhost:8000
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from slice.config import settings as load_settings
from slice.llm import complete
from slice.store import Store

from app import bank, report, roster

DB = Path(__file__).parent / os.environ.get("RECALL_DB", "webapp.db")
"""Which database this process writes to.

Two are kept deliberately separate:

    webapp.db   real people. Every row is someone who actually took the quiz,
                which is what makes it usable later as evidence that state
                persisted across sessions.
    demo.db     ten simulated students with designed misconceptions, for
                rehearsing the teacher dashboard without inventing a cohort.

Mixing them would mean a class report that is part measurement and part
fiction, with no way to tell afterwards which rows were which.

    RECALL_DB=demo.db .venv/bin/python webapp.py
"""

app = FastAPI()
_settings = load_settings()
_store: Store | None = None
_store_lock = threading.RLock()
# FastAPI's sync route handlers each run in a worker thread from a pool. A
# plain sqlite3 connection defaults to rejecting any use from a thread other
# than the one that opened it - every request landing on a different worker
# thread than the one that first called store() crashed with "SQLite objects
# created in a thread can only be used in that same thread." Caught this
# live: 16 of 364 real /answer submissions (about 4.4%) failed with a 500
# before this fix, which is what looked like a student's quiz "getting
# stuck" - the request had actually failed, not stalled.
#
# check_same_thread=False lifts that restriction, but is not enough on its
# own: a bare sqlite3.Connection is not safe to call from two threads AT THE
# SAME TIME even once that flag is set - confirmed with a 20-thread
# stress test that reliably raised InterfaceError without a lock, and passed
# clean with one. So every .execute()/.executescript() call on the
# connection is routed through _LockedConnection below, which every caller
# reaches automatically via store().db - including app/roster.py's raw
# `store.db.execute(...)` calls, not just the Store class's own methods.
# RLock, not Lock: some request paths call store() more than once while
# already holding it (nested calls would deadlock on a plain Lock).

class _LockedConnection:
    """Wraps a sqlite3.Connection so every query serialises through one lock,
    while everything else (row_factory, close, ...) passes through untouched."""

    def __init__(self, conn, lock):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_lock", lock)

    def execute(self, *a, **kw):
        with self._lock:
            return self._conn.execute(*a, **kw)

    def executescript(self, *a, **kw):
        with self._lock:
            return self._conn.executescript(*a, **kw)

    def executemany(self, *a, **kw):
        with self._lock:
            return self._conn.executemany(*a, **kw)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def store() -> Store:
    global _store
    with _store_lock:
        if _store is None:
            _store = Store(DB, check_same_thread=False)
            _store.db = _LockedConnection(_store.db, _store_lock)
            roster.init(_store)
        return _store


# ----------------------------------------------------------------------- chrome

CSS = """
/* Light, plain, unbranded. No violet, no gradients, and every answer option
   the same colour - a coloured option set (Kahoot-style red/blue/yellow/green)
   reads as a hint about which answer is which, and a tester picking by colour
   is not answering the question. */
:root{
  --bg:#faf7f0;        /* warm off-white */
  --card:#ffffff;
  --ink:#2b2b28;
  --muted:#6f6b63;
  --line:#e6e0d4;      /* beige rule */
  --accent:#006039;    /* Rolex green, used sparingly */
  --accent-soft:#eef2ed;
}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;
 background:var(--bg);color:var(--ink);min-height:100vh;line-height:1.55}
.wrap{max-width:680px;margin:0 auto;padding:1.5rem 1.15rem 4rem}
.wide{max-width:980px}
h1{font-size:1.45rem;margin:.2rem 0 .5rem;line-height:1.3;font-weight:600}
h2{font-size:1rem;margin:1.6rem 0 .5rem;color:var(--ink);font-weight:600}
p{margin:.6rem 0}
.muted{color:var(--muted);font-size:.92rem}
a{color:var(--accent)}
.brand{font-weight:700;font-size:1.05rem;color:var(--ink);padding:1rem 0 .1rem;
 display:block;text-decoration:none;letter-spacing:-.01em}
label{display:block;font-size:.85rem;color:var(--muted);margin:.9rem 0 .25rem}
input,select{width:100%;padding:.75rem .85rem;font-size:1rem;border-radius:8px;
 border:1px solid var(--line);background:#fff;color:var(--ink)}
input:focus,select:focus{outline:2px solid var(--accent);border-color:transparent}
button.go{width:100%;margin-top:1.4rem;padding:.9rem;font-size:1.02rem;
 font-weight:600;border:none;border-radius:8px;background:var(--accent);
 color:#fff;cursor:pointer}
button.go:hover{background:#00492c}
button.go:disabled{background:#9db3a8;cursor:wait}

/* Progress: solid Rolex green, no gradient. */
.bar{height:6px;background:var(--line);border-radius:99px;overflow:hidden;margin:.7rem 0 0}
.bar i{display:block;height:100%;background:var(--accent)}
.meta{display:flex;justify-content:space-between;align-items:center;
 font-size:.82rem;color:var(--muted);margin-bottom:.3rem}
.chip{display:inline-block;font-size:.8rem;color:var(--muted)}
.q{font-size:1.22rem;font-weight:600;line-height:1.4;margin:1.2rem 0 1.3rem}

/* Every option identical. */
.opts{display:grid;gap:.6rem}
.opt{width:100%;text-align:left;padding:.95rem 1.05rem;font-size:1rem;
 border:1px solid var(--line);border-radius:6px;background:var(--card);
 color:var(--ink);cursor:pointer;font-weight:400;line-height:1.45;
 transition:border-color .12s;font-family:inherit}
.opt:hover{border-color:var(--accent)}
.opt:disabled{opacity:.45;cursor:wait}
.k{font-weight:700;color:var(--muted);margin-right:.6rem}

.card{background:var(--card);border:1px solid var(--line);border-radius:6px;
 padding:1rem 1.15rem;margin:.7rem 0}
.card.key{border-left:3px solid var(--accent)}
.big{font-size:2.6rem;font-weight:700;letter-spacing:-.02em;color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:.93rem;margin-top:.4rem}
th{text-align:left;color:var(--muted);font-weight:600;font-size:.85rem;
 padding:.5rem .55rem;border-bottom:1px solid var(--line)}
td{padding:.6rem .55rem;border-bottom:1px solid var(--line)}
.pct{display:inline-block;min-width:3rem;font-variant-numeric:tabular-nums}
.sb{display:inline-block;width:76px;height:7px;background:var(--line);
 border-radius:99px;overflow:hidden;vertical-align:middle;margin-left:.5rem}
.sb i{display:block;height:100%}
.trail{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;
 color:var(--muted);background:#f4f1ea;border:1px solid var(--line);
 border-radius:8px;padding:.8rem 1rem;margin-top:.5rem;white-space:pre-wrap}
.row{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1.4rem}
.row a{flex:1;text-align:center;padding:.75rem;background:var(--card);
 border:1px solid var(--line);border-radius:8px;text-decoration:none;
 color:var(--ink);font-size:.92rem;min-width:8rem}
.row a:hover{border-color:var(--accent)}

/* Shown while the report is being written. Without it the page simply sits
   there for 15-30s and people assume it has hung. */
#waiting{display:none;text-align:center;padding:3rem 1rem}
#waiting.on{display:block}
.spin{width:34px;height:34px;margin:0 auto 1.1rem;border-radius:50%;
 border:3px solid var(--line);border-top-color:var(--accent);
 animation:sp .9s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
"""


def page(body: str, wide: bool = False) -> HTMLResponse:
    return HTMLResponse(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Recall</title><style>{CSS}</style></head><body>"
        f'<div class="wrap{" wide" if wide else ""}">{body}</div></body></html>'
    )


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def bar(correct: int, asked: int) -> str:
    """A score and a plain green fill.

    One colour, not a red/amber/green scale: the fill shows how much, and the
    report says in words whether that is a problem. Two things saying the same
    thing lets them disagree.
    """
    frac = (correct / asked) if asked else 0
    return (f'<span class="pct">{correct}/{asked}</span>'
            f'<span class="sb"><i style="width:{frac*100:.0f}%;'
            f'background:var(--accent)"></i></span>')


# ------------------------------------------------------------------ 1. signup

@app.get("/", response_class=HTMLResponse)
def signup():
    opts = "".join(f'<option value="{k}">{esc(v)}</option>'
                   for k, v in bank.DEPARTMENTS.items())
    return page(f"""
<a class="brand" href="/">Recall</a>
<h1>Diagnostic quiz</h1>
<p class="muted">20 questions across 5 topics. You will not be told whether
each answer is right — you get one consolidated report at the end.</p>
<form action="/start" method="post" id="signup" onsubmit="this.querySelector('button').disabled=true; this.querySelector('button').textContent='Starting\u2026'">
  <label>Name</label>
  <input name="name" required autofocus autocomplete="name">
  <label>Phone number</label>
  <input name="phone" required inputmode="tel" autocomplete="tel">
  <label>Register number</label>
  <input name="register_no" required autocomplete="off">
  <label>Department</label>
  <select name="department">{opts}</select>
  <button class="go" type="submit">Start the quiz</button>
</form>
<p class="muted" style="margin-top:2rem">
  Teacher? <a href="/teacher">Open the dashboard</a></p>
""")


@app.post("/start")
def start(name: str = Form(...), phone: str = Form(...),
          register_no: str = Form(...), department: str = Form(...)):
    if department not in bank.DEPARTMENTS:
        department = "computer_science"
    sid = roster.create_student(store(), name.strip(), phone.strip(),
                                register_no.strip(), department)
    return RedirectResponse(f"/quiz/{sid}", status_code=303)


# -------------------------------------------------------------------- 2. quiz

@app.get("/quiz/{sid}", response_class=HTMLResponse)
def quiz(sid: str):
    s = store()
    stu = roster.student(s, sid)
    if not stu:
        return RedirectResponse("/", status_code=303)

    questions = bank.for_department(stu["department"])
    done = roster.answered_ids(s, sid)
    remaining = [q for q in questions if q.id not in done]
    if not remaining:
        return RedirectResponse(f"/report/{sid}", status_code=303)

    q = remaining[0]
    n = len(questions) - len(remaining) + 1
    total = len(questions)

    opts = "".join(
        f'<button class="opt" type="submit" name="chosen" value="{o.key}">'
        f'<span class="k">{o.key}</span>{esc(o.text)}</button>'
        for o in q.options
    )

    # Only the last answer triggers the report, which takes 15-30s while the
    # model writes it. Every other answer is one SQL insert and a redirect -
    # showing a spinner for that would invent a delay that is not there.
    last = len(remaining) == 1
    waiting_title = ("Reading your answers&hellip;" if last
                     else "Saving&hellip;")
    waiting_note = ("This takes a few seconds. Please don't close the page."
                    if last else "")
    waiting_js = ("document.getElementById('waiting').classList.add('on');"
                  if last else "")
    return page(f"""
<div class="meta">
  <span>Question {n} of {total}</span>
  <span class="chip">{esc(q.topic)}</span>
</div>
<div class="bar"><i style="width:{(n-1)/total*100:.0f}%"></i></div>
<div class="q">{esc(q.prompt)}</div>
<form action="/answer" method="post" id="qform" onsubmit="submitting()">
  <input type="hidden" name="sid" value="{sid}">
  <input type="hidden" name="qid" value="{q.id}">
  <input type="hidden" name="shown" value="{time.time()}">
  <div class="opts">{opts}</div>
</form>
<div id="waiting">
  <div class="spin"></div>
  <p><b>{waiting_title}</b></p>
  <p class="muted">{waiting_note}</p>
</div>
<script>
function submitting() {{
  // Disabling the clicked button here, inside onsubmit, is what broke this:
  // a disabled control's name=value pair is dropped from form submission by
  // spec, so disabling ALL the option buttons - including the one just
  // clicked - stripped `chosen` out of the POST entirely, and every answer
  // failed with "Field required". Deferring the disable to the next tick lets
  // the browser finish reading the form first.
  setTimeout(() => {{
    document.querySelectorAll('#qform button').forEach(b => b.disabled = true);
  }}, 0);
  {waiting_js}
}}
</script>
<p class="muted" style="margin-top:1.4rem">No feedback until the end — answer
what you actually think.</p>
""")


@app.post("/answer")
def answer(sid: str = Form(...), qid: str = Form(...), chosen: str = Form(...),
           shown: float = Form(0.0)):
    # One insert. No model call on this path at all - that is what keeps the
    # quiz instant with a room full of people on it, and what keeps the answers
    # independent of each other.
    q = bank.by_id(qid)
    roster.record(store(), sid, q, chosen,
                  seconds=max(0.0, time.time() - shown) if shown else 0.0)
    return RedirectResponse(f"/quiz/{sid}", status_code=303)


# ------------------------------------------------------------------ 3. report

def _concept_cards(rows, css: str) -> str:
    if not rows:
        return '<p class="muted">Nothing in this group.</p>'
    return "".join(
        f'<div class="card {css}"><b>{esc(r["concept"])}</b> '
        f'<span class="chip">{esc(r["verdict"])}</span>'
        f'<p class="muted" style="margin:.45rem 0 0">{esc(r["evidence"])}</p></div>'
        for r in rows)


def _trail_html(body: dict) -> str:
    trail = body.get("_trail") or []
    if not trail:
        return ""
    lines = []
    for row in trail:
        if row["step"] == "draft":
            lines.append(f'draft  r{row["revision"]}  → {row["body"].get("headline","")[:70]}')
        else:
            b = row["body"]
            verdict = b.get("verdict", "")
            why = f'  ({b.get("failed_check")}) {b.get("detail","")[:80]}' if verdict == "rejected" else ""
            lines.append(f'check  r{row["revision"]}  → {verdict}{why}')
    revs = body.get("_revisions", 1)
    note = ("accepted first draft" if revs == 1
            else f"took {revs} drafts — the checker sent it back "
                 f"{revs-1} time{'s' if revs > 2 else ''}")
    return (f'<h2>How this report was produced</h2>'
            f'<p class="muted">{note}.</p>'
            f'<div class="trail">{esc(chr(10).join(lines))}</div>')


@app.get("/report/{sid}", response_class=HTMLResponse)
def student_report(sid: str, force: int = 0):
    s = store()
    stu = roster.student(s, sid)
    if not stu:
        return RedirectResponse("/", status_code=303)

    got, asked = roster.score(s, sid)
    if asked == 0:
        return RedirectResponse(f"/quiz/{sid}", status_code=303)

    body = report.for_student(s, sid, _settings, call=complete, force=bool(force))

    topics = "".join(
        f'<tr><td>{esc(t["topic"])}</td><td>{bar(t["correct"], t["asked"])}</td></tr>'
        for t in roster.by_topic(s, sid))

    # The student's page carries no machinery: no draft trail, no reviewer
    # banner, no "what this cannot tell you", no re-run button and no link into
    # the teacher's dashboard. Those exist for us and for a judge, and they are
    # still in the database and on the teacher's side - but a student reading
    # their own result should meet a plain page, not an audit log.
    parts = [
        f'<a class="brand" href="/">Recall</a>',
        f'<p class="muted">{esc(stu["name"])} · '
        f'{esc(bank.DEPARTMENTS[stu["department"]])} · {esc(stu["register_no"])}</p>',
        f'<div class="big">{got}<span class="muted" style="font-size:1.25rem">'
        f'/{asked}</span></div>',
        f'<h1>{esc(body["headline"])}</h1>',
    ]

    if body.get("cross_topic_pattern"):
        parts.append(
            f'<div class="card key"><p style="margin:0">'
            f'{esc(body["cross_topic_pattern"])}</p></div>')

    for para in _prose(body.get("strengths"), body.get("gaps")):
        parts.append(f'<p>{esc(para)}</p>')

    parts.append(f'<h2>By topic</h2><table>{topics}</table>')
    parts.append(f'<h2>What to do next</h2><div class="card">'
                 f'{esc(body["next_step"])}</div>')
    parts.append('<p class="muted" style="margin-top:2rem">Thank you for taking '
                 'this quiz.</p>')
    return page("".join(parts))


def _prose(strengths, gaps) -> list[str]:
    """Turn the concept lists into two plain sentences a student can read.

    The cards these replace showed a concept name, a grey `strong`/`mixed`
    chip and a clipped evidence line - three of them side by side read as a
    grading rubric rather than as feedback, and the first real report showed
    seven near-identical `mixed` chips in a row.

    The concept names come from app/bank.py and are already written the way a
    student would say them, so they can be dropped straight into a sentence.
    """
    def names(rows):
        return [r["concept"] for r in (rows or [])]

    out = []
    good, bad = names(strengths), names(gaps)

    if good:
        out.append("You handled " + _join(good) + " well.")
    if bad:
        lead = "The part to work on is " if len(bad) == 1 else "The parts to work on are "
        out.append(lead + _join(bad) + ".")
        # One concrete example of what went wrong, so the advice is not abstract.
        first = (gaps or [{}])[0].get("evidence")
        if first:
            out.append(first[0].upper() + first[1:] if first else "")
    if not good and not bad:
        out.append("Your answers were spread fairly evenly, with no single "
                   "area standing out either way.")
    return [o for o in out if o]


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# ----------------------------------------------------------------- 4. teacher

@app.get("/teacher", response_class=HTMLResponse)
def teacher():
    s = store()
    cards = "".join(
        f'<a class="card" style="display:block;text-decoration:none;color:inherit"'
        f' href="/teacher/{k}"><b>{esc(v)}</b>'
        f'<p class="muted" style="margin:.4rem 0 0">'
        f'{roster.class_size(s, k)} student(s) with answers recorded</p></a>'
        for k, v in bank.DEPARTMENTS.items())
    return page(f"""
<a class="brand" href="/">Recall</a>
<h1>Teacher dashboard</h1>
<p class="muted">Pick a department to see how the class performed, then drill
into a single student.</p>
{cards}
""")


@app.get("/teacher/{dept}", response_class=HTMLResponse)
def teacher_class(dept: str, force: int = 0):
    s = store()
    if dept not in bank.DEPARTMENTS:
        return RedirectResponse("/teacher", status_code=303)

    n = roster.class_size(s, dept)
    if n == 0:
        return page(f"""
<a class="brand" href="/">Recall</a>
<h1>{esc(bank.DEPARTMENTS[dept])}</h1>
<div class="card">No answers recorded yet. Once a student takes the quiz the
agent has something to read.</div>
<div class="row"><a href="/teacher">Back</a></div>""")

    body = report.for_class(s, dept, _settings, call=complete, force=bool(force))

    topics = "".join(
        f'<tr><td>{esc(t["topic"])}</td><td>{bar(t["correct"], t["answered"])}</td></tr>'
        for t in roster.class_by_topic(s, dept))

    people = []
    for stu in roster.students_in(s, dept):
        got, asked = roster.score(s, stu["id"])
        if asked == 0:
            continue
        people.append(
            f'<tr><td><a href="/teacher/{dept}/{stu["id"]}">{esc(stu["name"])}</a>'
            f'<br><span class="muted">{esc(stu["register_no"])}</span></td>'
            f'<td>{bar(got, asked)}</td>'
            f'<td class="muted">{asked}/20 answered</td></tr>')

    hardest = "".join(
        f'<tr><td>{esc(q["topic"])}<br><span class="muted">{esc(q["concept"])}</span></td>'
        f'<td>{bar(q["correct"], q["answered"])}</td></tr>'
        for q in roster.class_by_question(s, dept)[:6])

    split = ""
    if body.get("split"):
        split = (f'<div class="card key"><b>The class splits here</b>'
                 f'<p style="margin:.5rem 0 0">{esc(body["split"])}</p></div>')

    warn = ""
    if body.get("_unverified"):
        warn = ('<div class="card bad"><b>Wording not signed off</b>'
                '<p class="muted" style="margin:.4rem 0 0">The counts and the '
                'strong/weak calls below are computed in code. The reviewer '
                'did not sign off on the phrasing.</p></div>')

    return page(f"""
<a class="brand" href="/">Recall</a>
<p class="muted">{esc(bank.DEPARTMENTS[dept])} · {n} student(s)</p>
<h1>{esc(body["headline"])}</h1>
{warn}{split}
<h2>Teach again</h2>{_concept_cards(body.get("teach_again"), "bad")}
<h2>Landed well</h2>{_concept_cards(body.get("solid"), "good")}
<h2>By topic</h2><table>{topics}</table>
<h2>Hardest questions</h2><table>{hardest}</table>
<h2>Students</h2><table>
<tr><th>Student</th><th>Score</th><th>Progress</th></tr>{"".join(people)}</table>
<h2>Next step</h2><div class="card">{esc(body["next_step"])}</div>
<h2>What this cannot tell you</h2>
<p class="muted">{esc(body["uncertainty"])}</p>
{_trail_html(body)}
<div class="row">
  <a href="/teacher/{dept}?force=1">Re-run the agent</a>
  <a href="/teacher">All departments</a>
</div>
""", wide=True)


@app.get("/teacher/{dept}/{sid}", response_class=HTMLResponse)
def teacher_student(dept: str, sid: str):
    return RedirectResponse(f"/report/{sid}", status_code=303)


# ------------------------------------------------------------------- 5. live

@app.get("/live", response_class=HTMLResponse)
def live(request: Request):
    """A rolling headcount, for the person running this, nobody else.

    Localhost only - the public ngrok tunnel forwards every path on this app,
    so without this check anyone holding the student-facing link could also
    reach /live just by guessing the path. `request.client.host` is the
    server's own view of who connected; a tunnelled request arrives from
    127.0.0.1 same as a real one, so this is checked by testing straight
    through the tunnel, not assumed from the code alone.

    Refreshes itself every 15s via a plain meta tag - no JS, nothing to break
    if a phone's browser is being awkward, and it survives a page reload the
    same way. Shows names and scores, not just counts - it's meant to answer
    "who's done and how did they do" at a glance while people are mid-quiz.
    """
    if request.client is None or request.client.host not in ("127.0.0.1", "::1"):
        return HTMLResponse("Not found", status_code=404)

    s = store()
    summary_rows = []
    student_rows = []
    total_done = total_seen = 0

    for dept, label in bank.DEPARTMENTS.items():
        people = roster.students_in(s, dept)
        done = sum(1 for p in people if roster.score(s, p["id"])[1] >= 20)
        seen = len(people)
        total_done += done
        total_seen += seen
        summary_rows.append(
            f"<tr><td>{esc(label)}</td><td>{done}</td>"
            f"<td class=\"muted\">{seen - done} still going</td>"
            f"<td class=\"muted\">{seen} total</td></tr>")

        for p in people:
            got, asked = roster.score(s, p["id"])
            finished = asked >= 20
            student_rows.append((
                p["created_at"],
                f"<tr><td>{esc(p['name'])}</td><td>{esc(label)}</td>"
                f"<td class=\"muted\">{esc(p['register_no'])}</td>"
                f"<td>{got}/{asked}</td>"
                f"<td class=\"muted\">{'Complete' if finished else 'In progress'}</td></tr>"))

    # Newest signup first, so a new arrival is visible at the top without
    # scrolling - the point of watching this live.
    student_rows.sort(key=lambda r: r[0], reverse=True)

    import datetime
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    return HTMLResponse(f"""<!doctype html><html lang="en">
<head><meta charset="utf-8">
<meta http-equiv="refresh" content="15">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recall — live</title><style>{CSS}</style></head>
<body><div class="wrap wide">
<a class="brand" href="/">Recall</a>
<h1>Live count</h1>
<div class="big">{total_done}<span class="muted" style="font-size:1.2rem">
 /{total_seen} finished</span></div>
<p class="muted">Refreshes every 15 seconds. Last updated {stamp}.</p>
<table><tr><th>Department</th><th>Finished</th><th></th><th></th></tr>
{"".join(summary_rows)}</table>
<h2>Students</h2>
<table><tr><th>Name</th><th>Department</th><th>Register No.</th>
<th>Score</th><th>Status</th></tr>
{"".join(r[1] for r in student_rows)}</table>
</div></body></html>""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
