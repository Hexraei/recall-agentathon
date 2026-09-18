# Recall

A learning companion that reads each new piece of student work, compares it with
that student's earlier record, and surfaces evidence-backed candidate learning
gaps for a professor to decide on.

One professor, ~120 Data Structures students, one semester. The same gap turns
up in different forms across different tasks — a tutorial in week 3, an
assignment in week 7 — and with 120 students nobody connects those moments.
Recall connects them, refuses to overstate what it found, and asks the professor
before anything consequential happens.

**Team Mavericks** — Navin V, Barathkumar M P · CEG ASTRA Agent-a-thon, Sept 2026

---

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install pydantic httpx pytest
.venv/bin/python demo.py          # the whole story
.venv/bin/python demo.py --replay # plus every record, in order
./test.sh                         # 20 tests
```

No API key needed. Everything below runs on canned responses — that is phase 1,
and it is deliberate: the state machine, the back-edge, the suspend/resume and
the second encounter are all demonstrable before a single token is spent.

## What the demo shows

| | |
|---|---|
| **Encounter 1** | Mira, week 3. No history. The system records a first signal and explicitly does *not* claim a pattern. |
| **Encounter 2** | Mira, week 7, a different task. Reads encounter 1's records, finds the recurrence — then the checker **rejects** the first finding for overstating it, sends it backwards, and the redraft passes. Suspends on the professor because a recurring pattern is consequential. |
| **Negative control** | Arun. A superficially similar mistake with a different cause, against a real but unrelated history. Must come back `similar`, never `recurring`. |
| **Duplicate** | Mira resubmits assignment 1. Refused at ingest, because a duplicate would fake a second encounter. |

## Why this is an agent, not a pipeline

- **State survives the run.** Each submission is its own run; records live in
  SQLite, append-only, enforced by database triggers. A later run for the same
  student reads the earlier ones. Kill the process mid-run and nothing is lost.
- **A step sends work backwards.** The evidence check rejects a finding and
  routes it back — to extraction if the citations are wrong, to comparison if
  the reading of the evidence is. How many times that happens is decided by the
  run.
- **A person is a state, not a blocking call.** `NEEDS_REVIEW` is suspended, not
  terminal. The process may exit entirely; a later invocation picks the run up.
- **Two separate bounds.** A spend limit (tokens, attempts) and a revision limit
  (three findings, counted from the record history). They never share a counter.

## Layout

```
slice/          the starter kit's spine — durable store, budget, callback, runner
app/
  schema.py     the records every boundary returns
  flow.py       the handlers, the transitions, and the rules      ← the domain
  provenance.py the citation check. Deterministic. Asks no model
  history.py    reading one student's earlier runs
  stub.py       canned answers, so everything runs with no key
  fixtures.py   the three hand-written encounters
  prompts/      extract · compare · finding · check
corpus/         the course notes evidence is checked against
tests/          20 tests: provenance, the back-edge, resume, injection
```

`slice/` is copied from [agentic-slice-kit](https://github.com/rsimhan/agentic-slice-kit)
and is not ours. One edit: `RunState` shipped with another domain's six states
baked into it, so ours were added. Additive, and the runner treats them
opaquely.

## What it deliberately does not do

1. Make grading decisions, or prescribe an intervention without review.
2. Diagnose conditions or fixed ability, or label a student. Findings describe
   **work**, never a person — a finding that says "does not understand" is
   rejected by the checker, and there is a test for it.
3. Treat a single mistake as a recurring misconception. Recurrence needs
   evidence from more than one assignment, and that is enforced in code, not
   asked of the model.
4. Invent evidence. Every passage must appear verbatim in a document the run
   loaded. A row that fails is kept and marked *could not establish*, never
   dropped.
5. Claim the professor was consulted when they were not. `not_asked`,
   `no_reply` and a real decision are three different outcomes in the output.

## Known limits

- **One course.** Data Structures only. Whether this generalises to design or
  lab courses is untested, not merely uncertain.
- **Phase 1.** The model calls are stubbed. The prompts are written and the
  contracts are typed, but no real model has been run against them yet — so
  nothing here demonstrates that a model can hold these contracts. That is the
  next phase and the first thing to verify.
- **Recurrence threshold.** Two assignments is a domain opinion, not a finding.
  It is the number to argue about with a real professor.
