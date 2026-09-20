# Recall

A diagnostic quiz that remembers. A student's mistakes are compared against
their *own* earlier attempts — not a class average, not a rubric — and the
system only claims a pattern recurred when it can cite the exact earlier
answer that proves it. When a claim is consequential, it stops and asks a
human instead of deciding alone.

**Team Mavericks** — Navin V, Barathkumar M P, Jasper (`404jaspernotfound`) ·
CEG ASTRA Agent-a-thon, Sept 2026

---

## What this actually is

A 20-question diagnostic (robotics or computer science), taken by real
students at this event. Three things happen on top of the raw answers:

1. **A personal report**, generated once a student finishes — what they got
   right, what they got wrong, whether the wrong answers share one cause, and
   what to try next. One real model call, drafted, checked by code, and
   redrafted if the check rejects it — not templated text.
2. **A teacher dashboard**, per department — the same kind of report, over
   the whole class, plus a per-student drill-down.
3. **Persistent memory across sittings** — the feature the project is
   actually about. See below.

Everything runs through one FastAPI process (`webapp.py`), served for this
event over an ngrok tunnel. `RUN.md` has the exact commands to bring it up on
your own machine, including a working API key so nobody has to sign up for
one mid-review.

## The persistent-memory claim, and how to see it for yourself

The interesting failure mode a diagnostic quiz can catch is not "got this
question wrong" — it's "keeps making the *same* mistake across separate
attempts, weeks apart." A two-day event cannot produce that naturally, so the
demo is built honestly around a real constraint: **every answer is real, only
the calendar is fabricated.** Several real students' real answers are
replayed as one identity's sequential sittings, spaced three weeks apart in
the data. Full disclosure and the exact method: `docs/memory-demo.md`.

Two ways to watch it happen, both live in the browser at `/teacher/memory`:

- **`/teacher/memory/simple`** — the fast version. Pick a department and a
  chain length (2, 3, or 4 sittings), hit **Run it live**, and watch a real
  model call decide, in front of you, whether a real repeated mistake is
  the same mistake again. Robotics chains are built from students who share
  one exact, identical wrong answer — the system should converge cleanly on
  "recurring." Computer science chains use students with genuinely different
  mistakes — no single misconception dominates that department, so the
  system should stay honestly uncertain rather than force a match. Showing
  both back to back is the actual point: the system says "recurring" because
  the data supports it, not because it was asked to find something.
  When it does flag a recurrence as consequential, the page shows a real
  **Confirm / Reject** decision — wired to the same human-in-the-loop
  mechanism every review in this project goes through, not a cosmetic
  button.
- **`/teacher/memory`** — the full picture. Six built identities (four
  hand-picked within a department, two chosen at the department level by
  measuring the whole real cohort first — see
  `docs/memory-demo-department-selection.md`), each with a full sitting-by-
  sitting timeline and, per sitting, the exact answers the system cited.

Nothing on these pages is templated copy. `outcome`/`label` fields come
straight from a stored model decision; free text is the model's own
sentences, scrubbed only of internal question-ids so a reader sees a concept
name instead of a database key.

## Run it

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python webapp.py            # http://localhost:8000
```

No key, no network, architecture only:

```bash
.venv/bin/python demo.py              # the whole story on canned responses
.venv/bin/python demo.py --replay     # plus every record, in order
```

One real model call, end to end, terminal only:

```bash
.venv/bin/python live.py --full       # two encounters: nothing found, then found and suspended
```

Full instructions for every path (Windows included, and the working key for
a fresh machine) are in **[`RUN.md`](RUN.md)** — that file, not this one, is
the canonical "how do I start this" reference.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q   # 107 passed
```

## Why this is an agent, not a pipeline

- **State survives the run.** Every submission is its own append-only run in
  SQLite, enforced by database triggers — no `UPDATE`, no `DELETE`. A later
  run for the same identity reads every earlier one. Kill the process
  mid-run and nothing is lost.
- **A step sends work backwards.** Two back-edges, routed by *why* a claim
  failed: a citation problem returns to extraction; a claim-strength problem
  returns to comparison. This isn't hypothetical — `docs/evidence/` has real
  runs where it fired.
- **A person is a state, not a blocking call.** `NEEDS_REVIEW` suspends the
  run; the process can exit entirely, and a later invocation (or a click on
  Confirm/Reject in the live demo) picks it back up.
- **Two separate bounds, never sharing a counter.** A spend limit (tokens,
  attempts) and a revision limit (findings redrafted). Composing bounded
  limits into an unbounded one is a real bug this project found — see
  evidence 02 below.
- **Counts come from SQL, never the model.** Class size, how many chose an
  option, a score out of 20 — computed in code and handed to the model as
  fact. The model's job is to say what the numbers mean, never to produce
  one that gets shown to a person or checked against.

## Evidence — what we tested, what broke, why we fixed it that way

[`docs/evidence/`](docs/evidence/README.md) is eight real, measured defects
found on this project, plus one evaluation of a second model-based checker
that was tried and shelved. Not planted for a writeup — each one names the
measurement that surfaced it, the wrong first guess, and why the actual fix
is the right one rather than the convenient one.

| # | Defect | Found by |
|---|---|---|
| [01](docs/evidence/bug-01-report-truncation.md) | Report agent crashed on the lowest-scoring student | Running the full cohort, not one happy path |
| [02](docs/evidence/bug-02-composing-timeouts.md) | Three correctly-set timeouts composed into a 39-minute hang | An accidental network outage mid-run |
| [03](docs/evidence/bug-03-biased-compare-prompt.md) | The comparison step was wrong 9 times in 10 | Measuring a fixed input 10× instead of assuming model flakiness |
| [04](docs/evidence/bug-04-empty-structured-fields.md) | 59% of real reports dropped a real strength or gap from the structured fields | Reviewing 22 real students' reports against the counts |
| [05](docs/evidence/bug-05-checker-hallucinated-contradictions.md) | The checker rejected true sentences, citing the numbers that proved them | Reading every rejection reason across the cohort |
| [06](docs/evidence/bug-06-evidence-that-said-nothing.md) | Two-thirds of reports repeated themselves; half the sentences said nothing | Measuring report *quality*, not just pass/fail |
| [07](docs/evidence/bug-07-silent-degradation.md) | The fast provider was down for the day and nothing said so | Noticing a run took 411s when an earlier one took a fraction of that |
| [08](docs/evidence/bug-08-mislabelled-negative-control.md) | The demo's "no pattern" control had a real pattern in it — twice | Reading the citation instead of trusting the label |

Through-line, and what is explicitly **not yet tested**: see
[`docs/evidence/README.md`](docs/evidence/README.md). A separate,
evaluated-but-not-merged attempt at a model-based second judge (`typesafe/jev-1.13`)
is documented in [`docs/jev/`](docs/jev/README.md) — real work, deliberately
kept out of the judged path; `main`'s checks stay fully code-based.

## Layout

```
webapp.py         the whole app - quiz, personal report, teacher dashboard,
                  persistent-memory demo (browser + JSON API)
app/
  flow.py         the handlers, transitions, back-edges         ← the domain
  report.py       the personal/class report agent (draft → check → redraft)
  quiz.py         turns a raw answer into evidence, no model involved
  roster.py       every count the model is handed - SQL, not opinion
  memory_api.py   read-only JSON for the Flutter app's memory screens
  report_api.py   read-only JSON for the Flutter app's report screen
  simple_live_demo.py   the one-button live persistent-memory demo
  bank.py         the 20-question bank per department, with misconceptions
  prompts/        extract · compare · finding · check, per surface
slice/            the starter kit's spine - durable store, budget, callback,
                  runner. Copied from agentic-slice-kit; not ours, not edited.
frontend_flutter/ the mobile app - same read-only APIs, same disclosure rules
tools/            builds and runs the persistent-memory demo data
docs/             everything that isn't code - see docs/evidence/ especially
tests/            107 tests - the flow, the quiz app, the memory API, Jev
corpus/           course notes evidence is checked against
```

## What it deliberately does not do

1. Make grading decisions, or prescribe an intervention without review.
2. Diagnose a person or a fixed ability. Findings describe **work** — a
   finding phrased as "doesn't understand X" is rejected by the checker, and
   there's a test for it.
3. Treat one mistake as a recurring pattern. Recurrence needs evidence from
   more than one sitting, enforced in code, never asked of the model as a
   favour.
4. Invent evidence. A citation must appear verbatim in an answer the run
   actually read. A claim that fails this is kept and marked, never silently
   dropped.
5. Claim a professor was consulted when they weren't. `not_asked`, `no_reply`,
   and an actual decision are three different, distinguishable outcomes.
6. Show a mobile-app or web-app viewer anything a real model call didn't
   produce. The memory/report JSON APIs are read-only by design — see their
   own docstrings.

## Known limits

- **Two departments.** Robotics and computer science, twenty questions each.
  Whether this generalises to other subjects is untested, not just uncertain.
- **The recurrence threshold (two sittings) is a domain opinion**, not a
  proven constant — the number worth arguing with a real professor about.
- **Degraded-network behaviour is undertested by design** — found by
  accident once (evidence 02), not by systematic fault injection.
- See `docs/evidence/README.md`'s own "what we have not tested" section for
  the rest, stated as plainly as the wins.
