# Build log: the persistent-memory demo

A record of how the demo in [`memory-demo.md`](memory-demo.md) was built, in the
order it happened, including the two things we got wrong and how they surfaced.
Written so someone picking this up cold knows not just what exists but why it
has the shape it has.

---

## The problem

The system's central claim is that it notices when a student's *current* mistake
repeats one they made *before*. `app/history.py:prior_records()` reads a
student's earlier runs; `app/flow.py:handle_comparing()` decides whether the
current work relates to them.

That needs **the same person submitting on separate occasions.** At the time of
this work, 31 real students had completed the 20-question diagnostic — each of
them exactly once. Twenty single snapshots are not a longitudinal record, and
nobody sits a diagnostic quiz four times in a two-day hackathon.

The plan, already committed to in
[`progress-report-day1-afternoon.md`](progress-report-day1-afternoon.md): group
real students into synthetic identities, replay their real answer-sets as
sequential sittings by one person, and **say plainly that only the timeline is
constructed.**

---

## Step 1 — Confirming the replay was even possible

Read before writing anything:

- `app/history.py` — `_runs_for()` matches on `runs.meta_json.student_id` and
  orders by `created_at`. **It has no idea where the underlying rows came from.**
  That is what makes the replay exercise the real detection path rather than a
  mock.
- `app/flow.py` — `handle_comparing`, and the `RECURRENCE_NEEDS_ATTEMPTS = 2`
  rule that downgrades a `recurring` claim in *code* if it is not backed by two
  different assignments.
- `app/quiz.py:attempt_from_answer()` — the attempt shape, including
  `precomputed_evidence`, which skips the extraction model call entirely.
- `slice/store.py` — append-only `versions` table, enforced by SQLite triggers.

One surprise worth recording: the live webapp only ever creates `recall_report`
runs. **It has never run the `recall` agent flow at all.** So the longitudinal
runs are a new artifact and collide with nothing.

## Step 2 — Two decisions taken with the user, not assumed

1. **Write to a separate `memory.db`**, copied from `webapp.db`. Real students
   were still submitting; the fabricated timeline has no business in the
   production file.
2. **One sitting = one whole 20-question quiz** (`assignment_id` like
   `diagnostic_sitting_1`), not one question. Four sittings = four assignments,
   so recurrence is reachable and "one person sat the quiz four times" reads as
   a real story.

## Step 3 — Picking the groups from real data

Profiled all 31 students' wrong answers by concept, then searched
combinatorially for two kinds of group per department:

- **Category A** — a concept every member gets wrong. Best find: four CS
  students where three picked the *identical* wrong option on `cs_t4_q1`
  ("treated `b = a` as making a copy").
- **Category B** — no shared concept, meant as the negative control.

Selection read `roster.by_concept` / `misconceptions` **directly**, never the
generated reports, because the "empty structured fields" finding in
[`docs/evidence`](evidence/) shows 59% of real reports omit a genuine strength
or gap from their structured fields.

## Step 4 — `tools/build_memory_demo.py`

Copies the DB, then per sitting: creates a `recall` run tagged with the
synthetic `student_id`, writes the real answers as the `attempt` +
`precomputed_evidence`, and **backdates `created_at`** to the fabricated
calendar (three weeks apart) — because that is what `history.py` orders by.

Evidence is capped at 8 items by `app/schema.py`, and a sitting has 20 answers,
so wrong answers are taken first and correct ones fill the remainder.

Every sitting carries its own provenance in `quiz_meta`:
`replayed_from_real_student`, `replayed_from_real_name`,
`synthetic_timeline: true`.

---

## Mistake 1 — advancing only the last sitting

First replay: **every group returned `not_enough_evidence`**, including the
clean Category A ones. The trace said `0 evidence rows from 0 earlier
assignments`.

Cause: `prior_records()` reads the `evidence` rows earlier runs **wrote**, and a
run only writes them when it is *advanced*. Four sittings had been built but
only the last was run, so its history was legitimately empty.

Fix: `run_memory_demo.py` advances **every sitting in chronological order**.
Each sitting has to genuinely happen before the next can remember it. This is
now documented in the runner's docstring, because it is the single easiest thing
to get wrong when re-running the demo.

## Mistake 2 (twice) — the negative control had a real pattern in it

With the ordering fixed, both Category A groups found their recurrence. But
Category B returned `recurring` too — apparently a false positive.

**It was not.** Reading the citation: two members had picked the **identical
wrong option on the identical question** (`cs_t1_q1`, distractor B). The agent
cited exactly that pair. By the comparison prompt's own test — *would one
explanation fix both?* — that is recurrence.

Tightened the rule to "no shared wrong **question**" and re-ran. It returned
`recurring` **again** — this time citing two *different* questions resting on one
misconception about reference semantics (`b = a` as a copy, `y = x` as a
permanent link). Again accurate.

**Twice the pipeline was right and our label was wrong.** The comfortable
conclusion was "the model over-claimed" — comfortable because it blames the
model rather than the person who built the test.

Written up as
[`bug-08`](evidence/bug-08-mislabelled-negative-control.md). The final rule: a
group advertised as a clean control shares no wrong question **and** no wrong
concept, enforced by `validate()` at build time so the build *fails* rather than
producing a confusing demo.

**The honest cost, recorded not hidden:** with 5 CS concepts and 13 completed
students, **no clean control of four exists in computer science at all.** That
group ships labelled a near-miss and is scored on a different question — not
"did it stay silent" but "when it claimed, did it cite and defer to a human."

## Step 5 — Scoring that matches how each group was built

Reading only the final sitting turned ordinary model variance into a pass/fail.
Scoring now runs across every sitting that had a history, and differs by group
type: Category A = found it at least once; clean control = never claimed one;
near-miss = every claim cited its evidence and paused for a human.

### Results (real model calls, shipping pipeline)

| | identity | result |
|---|---|---|
| A | Priya R. (robotics) | found the recurrence **3 of 3** sittings with history |
| A | Arjun M. (CS) | **2 of 3** |
| B | Karthik S. (robotics, clean control) | **claimed no recurrence at all** |
| B | Nithya V. (CS, near-miss) | 1 claim — cited, paused for a human |

Arjun M. is reported as 2/3, not rounded up: sittings 2 and 3 found the
reference-semantics misconception, sitting 4 correctly called a weaker pairing
`similar` rather than forcing it.

---

## Step 6 — The mobile-app API

`app/memory_api.py`, mounted at `/api/memory`, built around one rule from the
user: **the app states what happened, never why.** The presenter explains the
failure live; a screen that diagnoses a cause either pre-empts that or
contradicts it.

So the API returns the agent's own label, explanation and citations, plus an
`outcome` word (`first` | `found` | `none_found`) for the UI, and carries **no
`why` / `reason` / `expected` field**. A test guards those field names, because
that is how an explanation would reach the UI by accident.

Also: read-only (own connection per request, all write methods 405), reads
`memory.db` not the live `webapp.db`, and every response carries the provenance
disclosure so the app cannot render the data without the honest framing.

[`FLUTTER_CONTEXT.md`](FLUTTER_CONTEXT.md) has the endpoint reference, the
three outcome states (`none_found` is a normal confident result, **not** an
empty state), and two honest ways to demo it failing.

---

## What to re-run

```bash
.venv/bin/python tools/build_memory_demo.py --force   # webapp.db -> memory.db
.venv/bin/python tools/run_memory_demo.py             # replay, in order
.venv/bin/python webapp.py                            # serves /api/memory
```

The build fails loudly if a group is not the category it claims to be.

**Throughout: `webapp.db` is opened read-only and never written to.** After
every run above it still contained zero `recall` runs.
