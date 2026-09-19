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

import time
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from slice.config import settings as load_settings
from slice.llm import complete
from slice.store import Store

from app import bank, report, roster

DB = Path(__file__).parent / "webapp.db"

app = FastAPI()
_settings = load_settings()
_store: Store | None = None


def store() -> Store:
    global _store
    if _store is None:
        _store = Store(DB)
        roster.init(_store)
    return _store


# ----------------------------------------------------------------------- chrome

CSS = """
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:0;
 background:#0f1020;color:#f2f2f7;min-height:100vh}
.wrap{max-width:720px;margin:0 auto;padding:1.5rem 1.1rem 4rem}
.wide{max-width:1000px}
h1{font-size:1.5rem;margin:.2rem 0 .4rem;line-height:1.25}
h2{font-size:1.05rem;margin:1.6rem 0 .6rem;color:#b9b9d6;
 text-transform:uppercase;letter-spacing:.06em}
p{line-height:1.55}
.muted{color:#9a9ab8;font-size:.9rem}
a{color:#8ab4ff}
.brand{font-weight:700;letter-spacing:-.02em;font-size:1.1rem;color:#fff;
 padding:1rem 0 .2rem;display:block;text-decoration:none}
label{display:block;font-size:.85rem;color:#b9b9d6;margin:.9rem 0 .25rem}
input,select{width:100%;padding:.75rem .85rem;font-size:1rem;border-radius:10px;
 border:1px solid #2e2e50;background:#181830;color:#fff}
input:focus,select:focus{outline:2px solid #6c5ce7;border-color:transparent}
button.go{width:100%;margin-top:1.4rem;padding:.9rem;font-size:1.05rem;
 font-weight:600;border:none;border-radius:10px;background:#6c5ce7;color:#fff;
 cursor:pointer}
button.go:hover{background:#7d6ef0}
.bar{height:6px;background:#22223f;border-radius:99px;overflow:hidden;margin:.8rem 0 0}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#6c5ce7,#00c2a8)}
.meta{display:flex;justify-content:space-between;align-items:center;
 font-size:.82rem;color:#9a9ab8;margin-bottom:.3rem}
.chip{display:inline-block;background:#22223f;border:1px solid #33335c;
 padding:.22rem .6rem;border-radius:99px;font-size:.76rem;color:#c9c9e8}
.q{font-size:1.3rem;font-weight:600;line-height:1.35;margin:1.2rem 0 1.3rem}
.opts{display:grid;gap:.7rem}
.opt{width:100%;text-align:left;padding:1.05rem 1.1rem;font-size:1rem;
 border:none;border-radius:12px;color:#fff;cursor:pointer;font-weight:500;
 line-height:1.4;transition:transform .06s}
.opt:hover{transform:translateY(-2px)}
.o0{background:#e0413e}.o1{background:#1668c4}.o2{background:#c9a227}
.o3{background:#1c8a4e}
.k{font-weight:800;opacity:.75;margin-right:.55rem}
.card{background:#181830;border:1px solid #2a2a4a;border-radius:14px;
 padding:1.1rem 1.2rem;margin:.8rem 0}
.card.good{border-left:3px solid #1c8a4e}
.card.bad{border-left:3px solid #e0413e}
.card.key{border-left:3px solid #6c5ce7;background:#1d1b3a}
.big{font-size:2.6rem;font-weight:700;letter-spacing:-.03em}
table{width:100%;border-collapse:collapse;font-size:.92rem;margin-top:.5rem}
th{text-align:left;color:#9a9ab8;font-weight:500;font-size:.78rem;
 text-transform:uppercase;letter-spacing:.05em;padding:.5rem .6rem;
 border-bottom:1px solid #2a2a4a}
td{padding:.6rem;border-bottom:1px solid #22223f}
tr:hover td{background:#191933}
.pct{display:inline-block;min-width:3.2rem}
.sb{display:inline-block;width:70px;height:7px;background:#22223f;
 border-radius:99px;overflow:hidden;vertical-align:middle;margin-left:.4rem}
.sb i{display:block;height:100%}
.trail{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;
 color:#9a9ab8;background:#13132a;border-radius:10px;padding:.8rem 1rem;
 margin-top:.6rem;white-space:pre-wrap;line-height:1.5}
.row{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}
.row a{flex:1;text-align:center;padding:.8rem;background:#22223f;
 border-radius:10px;text-decoration:none;color:#c9c9e8;font-size:.9rem;
 min-width:8rem}
.row a:hover{background:#2e2e52}
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


def _colour(frac: float) -> str:
    return "#1c8a4e" if frac >= .8 else "#c9a227" if frac >= .5 else "#e0413e"


def bar(correct: int, asked: int) -> str:
    frac = (correct / asked) if asked else 0
    return (f'<span class="pct">{correct}/{asked}</span>'
            f'<span class="sb"><i style="width:{frac*100:.0f}%;'
            f'background:{_colour(frac)}"></i></span>')


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
<form action="/start" method="post">
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
        f'<button class="opt o{i}" type="submit" name="chosen" value="{o.key}">'
        f'<span class="k">{o.key}</span>{esc(o.text)}</button>'
        for i, o in enumerate(q.options)
    )
    return page(f"""
<div class="meta">
  <span>Question {n} of {total}</span>
  <span class="chip">{esc(q.topic)}</span>
</div>
<div class="bar"><i style="width:{(n-1)/total*100:.0f}%"></i></div>
<div class="q">{esc(q.prompt)}</div>
<form action="/answer" method="post">
  <input type="hidden" name="sid" value="{sid}">
  <input type="hidden" name="qid" value="{q.id}">
  <input type="hidden" name="shown" value="{time.time()}">
  <div class="opts">{opts}</div>
</form>
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

    pattern = ""
    if body.get("cross_topic_pattern"):
        pattern = (f'<div class="card key"><b>Pattern across topics</b>'
                   f'<p style="margin:.5rem 0 0">{esc(body["cross_topic_pattern"])}</p></div>')

    warn = ""
    if body.get("_unverified"):
        # Precise about what is and is not verified. The scores, verdicts and
        # the cross-topic pattern are computed and checked in code, so they are
        # sound whatever the checker said; it is the WORDING that went out
        # without a second opinion. A banner implying the numbers are suspect
        # would be its own false claim.
        warn = ('<div class="card bad"><b>Wording not signed off</b>'
                '<p class="muted" style="margin:.4rem 0 0">The scores, the '
                'strong/weak calls and the cross-topic pattern below are '
                'computed and verified in code. The reviewer did not sign off '
                'on how this was phrased, so read the wording with that in '
                'mind.</p></div>')

    return page(f"""
<a class="brand" href="/">Recall</a>
<p class="muted">{esc(stu["name"])} · {esc(bank.DEPARTMENTS[stu["department"]])}
 · {esc(stu["register_no"])}</p>
<div class="big">{got}<span class="muted" style="font-size:1.2rem">/{asked}</span></div>
<h1>{esc(body["headline"])}</h1>
{warn}{pattern}
<h2>By topic</h2><table>{topics}</table>
<h2>Strengths</h2>{_concept_cards(body.get("strengths"), "good")}
<h2>Gaps</h2>{_concept_cards(body.get("gaps"), "bad")}
<h2>Next step</h2><div class="card">{esc(body["next_step"])}</div>
<h2>What this cannot tell you</h2>
<p class="muted">{esc(body["uncertainty"])}</p>
{_trail_html(body)}
<div class="row">
  <a href="/report/{sid}?force=1">Re-run the agent</a>
  <a href="/teacher">Teacher dashboard</a>
</div>
""")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
