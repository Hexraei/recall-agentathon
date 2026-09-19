# The persistent-memory demo: real answers, a constructed timeline

This is the demo for the one claim the whole system rests on — that it notices
when a student's *current* mistake is one they have made *before* — and this
document exists so that nobody has to guess which part of it is real.

## Say this part out loud

> **Every answer in this demo is a real answer from a real student.** Thirty-one
> people at this event sat the twenty-question diagnostic, and nothing in their
> responses has been edited, improved, or invented.
>
> **The only thing we fabricated is the calendar.** Three or four different real
> students are relabelled as one person sitting the quiz that many times, three
> weeks apart.
>
> We did that because the system is built to detect a mistake *recurring across
> separate occasions*, and nobody sits a diagnostic quiz four times during a
> two-day hackathon. Given a choice between inventing student answers and
> inventing dates, we invented the dates — the answers are the part that has to
> be real for the detection to mean anything.

This is the same commitment already written into
[`progress-report-day1-afternoon.md`](progress-report-day1-afternoon.md); the
demo does what that document said it would.

## Why the replay exercises the real thing

`app/history.py` builds a student's record by matching `runs.meta_json.student_id`
and ordering by `created_at`. It has no opinion about where the rows underneath
came from. So a synthetic identity whose sittings carry real answers under
fabricated dates goes through the *shipping* comparison path
(`app/flow.py:handle_comparing`) with nothing special-cased for the demo — same
prompt, same `RECURRENCE_NEEDS_ATTEMPTS` rule in code, same evidence-citation
check.

Two scripts, both re-runnable from scratch:

| | |
|---|---|
| `tools/build_memory_demo.py` | Copies `webapp.db` to `memory.db` and writes the sittings. **The production database is never written to** — real students are still submitting into it. |
| `tools/run_memory_demo.py` | Advances every sitting through the real flow, oldest first, and records what each concluded. |

Order matters in the second one, and it is the thing we got wrong first.
`prior_records()` reads the `evidence` rows earlier runs *wrote*, and a run only
writes them when it is actually advanced. Build four sittings, advance only the
last, and its history is legitimately empty — so even a real recurrence comes
back `not_enough_evidence`. Each sitting has to genuinely happen before the next
one can remember it.

## Two kinds of group, on purpose

**Category A — there is a pattern, and it should be found.** Members hand-picked
because their wrong answers really do land on one concept. Selected by reading
`roster.by_concept` / `misconceptions` rows directly, *not* the generated
reports: the "empty structured fields" finding in [docs/evidence](evidence/) records that 59% of
real reports drop a genuine strength or gap from their structured fields, so a
report's `gaps` list cannot be trusted to pick these.

**Category B — there is no pattern, and none should be claimed.** **This is the
harder half of the demo and the more important one.** A system that finds
patterns is easy; a system that declines to find one when there isn't one is the
difference between a tool a teacher can act on and a tool that generates
plausible-sounding busywork.

Category B comes in two strengths, and the difference is stated rather than
blurred:

- **`mem_robotics_b` is a true negative control.** Its sittings share no wrong
  question *and* no wrong concept. There is provably nothing to find, so
  anything the system reported would be an invention. It has three sittings, not
  four, for an honest reason: across 18 real robotics students, **no group of
  four with zero concept overlap exists.** Padding it to four would have
  smuggled a real pattern into the control.
- **`mem_cs_b` is a near-miss, not a control, and is labelled as such.** With
  only five CS concepts and 13 completed students, no clean group of four exists
  at all. No question is missed twice, but two sittings do touch
  *understanding what a variable holds*. That makes it a genuinely hard case
  rather than a clean negative — and a useful one, because a recurrence claim
  here has to cite that concept and let a professor judge whether two different
  questions on one concept is a pattern or a coincidence.

`validate()` in the builder enforces the distinction: a group flagged
`clean_control` that shares a concept fails the build.

## The negative control was wrong first, and the system caught it

Worth telling, because it is the strongest evidence here that the detection is
real and not staged.

The first Category B group was assembled on the rule "four students whose wrong
answers spread across five different concepts." The pipeline came back
`recurring`, which looked like a false positive.

It wasn't. Two of those four students had picked the **identical wrong option on
the identical question** — `cs_t1_q1`, distractor B, *"treated the work as fixed;
a loop that visits every item must do more work when there are more items."* The
agent cited exactly that and explained it correctly. By the comparison prompt's
own test — *would one explanation fix both?* — that is recurrence. The agent was
right and **our group label was wrong.**

So the selection rule got stricter — twice. First, Category B members had to
share no wrong *question*. That still wasn't enough: the system then found a
recurrence across two *different* questions that rest on the same misconception
about reference semantics (`b = a` making a copy, and `y = x` as a permanent
link). Again the citation was correct and the label was ours to fix. The rule is
now that a group advertised as a clean control shares no wrong **concept**
either, and `validate()` refuses to build one that does.

The honest cost of that rule is recorded above: in computer science no such
group of four exists, so `mem_cs_b` is published as a near-miss rather than
relabelled to look clean. **Twice the pipeline was right and our labelling was
wrong** — which is the most direct evidence available that the detection is
doing real work rather than reproducing what it was set up to say.

## What the system decides, and what it does not

The agent never issues a verdict on a student. It surfaces a pattern, or the
absence of one, or its own uncertainty — with the specific answers it is citing
— and a professor decides what that means and what to do.

That division is enforced in code, not left to the model's discretion:

- `RECURRENCE_NEEDS_ATTEMPTS` in `app/flow.py` downgrades any `recurring` claim
  that isn't backed by two different assignments, whatever the model believed.
- The citation check rejects a finding that cites an answer with no supported
  evidence row behind it.
- A finding judged consequential suspends the run at `NEEDS_REVIEW` and waits
  for a human rather than closing itself.

Category A shows the agent finding something real and defensible. Category B
shows it declining to invent one. **Both are the demo.** The second is not a
failure case we are being candid about — it is the behaviour that makes the
first one trustworthy.

## What it actually did

Every sitting below was advanced through the shipping flow against real Groq
calls. Full transcripts, including every citation, are in
[`memory-demo-results.json`](memory-demo-results.json).

| | identity | sittings | result |
|---|---|---|---|
| **A** | Priya R. (robotics) | 4 | found the recurrence on **3 of 3** sittings that had a history to read |
| **A** | Arjun M. (CS) | 4 | found it on **2 of 3** |
| **B** | Karthik S. (robotics, clean control) | 3 | **claimed no recurrence at all**, on either sitting with a history |
| **B** | Nithya V. (CS, near-miss) | 4 | 1 of 3 claimed a recurrence — cited, and paused for a human |

Read across the sittings, not just the last one. A single run is one sample of a
model, and reporting only the final sitting would turn ordinary variance into a
verdict.

**Priya R.** is the clean positive. Three separate sittings each independently
identify *backing a claim with a measurement*, citing `rb_t2_q4` across
different sittings — real answers from four different people, and the misconception
is genuinely the same one each time.

**Arjun M. is the honest one.** Sittings 2 and 3 both find the reference-semantics
misconception and cite it precisely — `b = a` treated as a copy, `y = x` treated
as a permanent link. Sitting 4 does not: it pairs a data-structure error with a
variable error and correctly labels that weaker pairing `similar` rather than
forcing it. **We are not reporting 3/3 here.** The detection is real and it is
not deterministic, and a judge is better served by the actual number.

**Karthik S. is the result the demo is built on.** Given three sittings with no
shared question and no shared concept, the system claimed nothing. It said
`similar` twice, and in both cases the explanation spells out *why* it stopped
short — "related but not caused by the same underlying misunderstanding." That
sentence is the product. A system that produced a confident finding here would
be worse than useless to a teacher, because they would have no way to tell that
one from a real one.

**Nithya V.** behaved exactly as the near-miss label predicts: one recurrence
claim, resting on the concept overlap we documented as unavoidable in CS, citing
both answers, and suspended at `NEEDS_REVIEW` for a professor instead of closing
itself. That is the correct handling of a judgement call — make the claim, show
the evidence, hand it to the human.

## Running it

```bash
.venv/bin/python tools/build_memory_demo.py --force   # webapp.db -> memory.db
.venv/bin/python tools/run_memory_demo.py             # replay through the real flow
```

The build step refuses to run if a group is not the category it claims to be.

Built from the 31 real students who had completed all twenty questions at the
time of the run (18 robotics, 13 computer science). Students still mid-quiz are
excluded — `read_sitting()` rejects anything short of a full twenty answers, so
a partial attempt can never become a sitting. Rebuilding later picks up whoever
has finished since.

**`webapp.db` is read-only throughout and is never written to.** After the run
above it contained zero `recall` runs; all 15 live in `memory.db`.

## On a phone

The mobile app reads this demo over a read-only JSON API
(`/api/memory`, [`app/memory_api.py`](../app/memory_api.py)) served from
`memory.db`. The app states *what* each sitting concluded and shows the answers
it cited; it deliberately carries no field explaining *why* a sitting came out
the way it did, because a person explains that live while the screen is up.
Build notes for it: [`FLUTTER_CONTEXT.md`](../FLUTTER_CONTEXT.md).
