# Bug 04 — the AI skips the structured fields more often than it fills them

**Found:** 19 September 2026, Day 1 evening, reviewing real students' reports for the first
time — not test data, not the simulated cohort in `demo.db`.
**Status:** confirmed, not yet fixed. Written up now as evidence of what real data
surfaced, ahead of the actual fix.
**Files:** `app/report.py`, `app/prompts/student_report.md`, `app/prompts/report_check.md`

---

## What we were doing

23 real students had finished the quiz by this point — the first batch of genuine data
this system has ever seen, as opposed to the ten hand-designed personas in `demo.db`.
Asked to review the AI-written reports and evaluate whether they were actually any good,
not just whether they ran without crashing.

## What we found

Pulled every completed report's structured fields (`strengths`, `gaps`) against the
underlying counts (`app/report.py`'s `verdict_for()` output, computed in code, not by the
model) for all 22 students who had a report generated:

**13 of 22 — 59% — have at least one concept the counts call `strong` or `weak` that
never appears in the report's `strengths` or `gaps` lists at all.**

Two students make the pattern impossible to miss:

- **Gokul, the lowest scorer in the batch at 4/20.** Every single concept in his data is
  `weak` or `mixed` — zero strong, four weak, one mixed. His report's `gaps` list is
  **empty**. The headline says "particularly around how code stops and how to prove a
  claim," which is true and specific — but that content never made it into the structured
  field the page actually renders as his gap list. The student who most needs a clear,
  itemised diagnosis got the least structured one.
- **Sathya Sa**, a strong performer (2 weak, 3 strong concepts): headline reads "You have
  a solid grasp of measurement and method selection, but the math behind movement and
  force needs a closer look" — naming specific strengths and a specific gap, in prose.
  `strengths: []`, `gaps: []`. Same shape as Gokul: real, specific content, written into
  the one field nobody asked it to fill, and left out of the two fields that were.

Checked whether this was one unlucky draft: pulled the raw model output before any
correction ran. In both cases, **the empty lists came out of the model's first draft**,
unchanged by anything downstream. The code-side checks (`enforce_verdicts`,
`check_claim_strength`) only look at entries that exist; neither one has a rule saying an
entry that should exist is missing. So this sails through every check we have, every time,
because none of the checks were built to catch an omission — only a false claim.

## Why this is a different kind of bug from the ones we'd already found

Every previous bug in this system — the truncated report, the composed timeouts, the
biased compare prompt, the checker's own false rejections — was the model **saying
something wrong**. This one is the model **saying nothing where it should say something
specific**, and folding the real content into a field that was never meant to carry it.
That's a harder failure to catch by construction, because "is this list too short" isn't
a claim you can check against the counts the way "is this number right" is — the counts
don't say how many entries a list must have, only what each entry would mean if it
existed.

It also means our headline field has quietly become a second draft of the report living
inside a field meant to be one sentence. Two students above wrote what amounts to a
condensed but real gaps-and-strengths write-up into their headline, because the model
found that an acceptable substitute for filling in the structured lists — and the checker
agreed, because the headline wasn't false.

## What we haven't fixed yet, and why we're writing this up before the fix

We're logging this now, with the real before-state, because the instinct after finding a
bug like this is to patch it immediately and move on — and the thing worth resisting is
writing the fix first and the evidence afterward, which tends to produce a tidier story
than what actually happened. The honest sequence is: found via real data, confirmed with a
full-batch count (13 of 22, not "a couple"), traced to the model's first draft rather than
a later corruption, and only then does the fix get written.

The likely direction, not yet built or measured: the writer's prompt
(`app/prompts/student_report.md`) needs an explicit rule that every `strong`/`weak`
concept from `by_concept` must appear in exactly one of `strengths` or `gaps` — no
folding it into the headline instead — and the checker needs a genuinely new kind of
check, one that looks at what's **absent** rather than only what's present and false.
That second part is new territory for this codebase; every check so far has been "is this
claim true," never "is this claim missing."

## What worked, in the same review

Not everything found was bad. Worth recording because an evidence file that only lists
failures undersells what actually held up on real data:

- **22 of 22 completed reports generated without crashing.** No `SchemaFailure`, no
  truncation — the fixes from bugs 01 and the token-cap tightening held under real,
  varied student data, not just our own test cohort.
- **The cross-topic pattern detection genuinely worked on real answers.** Dhanushree's
  report correctly identified "picking the right data structure" as one underlying gap
  showing up in two different topics (Lists and Loops, Storing Things) — not a planted
  case, a real student's real wrong answers. Yuvaraaja Ganesh V's report found the same
  thing across two robotics topics ("both treated a continuous effect as a one-time
  thing"). This is the actual point of the whole system, working on data nobody
  engineered to make it work.
- **The checker's false-rejection problem is real but small in this batch** — 1 of 22
  reports (Navin's) was flagged `_unverified`, and reading the trail shows the rejection
  was the checker misreading its own supporting evidence ("the counts show 1 wrong answer
  in 20" was used to reject a headline that said exactly that). Same failure mode as
  earlier sessions found in synthetic testing, now confirmed present on a real person's
  real report, at a similar low rate.

## Numbers, for whoever asks

- 23 real students completed the quiz; 22 had a report generated at review time.
- 13 of 22 (59%) have at least one `strong`/`weak` concept missing from the structured
  report.
- 1 of 22 (4.5%) was flagged unverified by the checker, for a false rejection.
- 0 of 22 crashed.

---

## Re-measured, 19 September 2026 (later the same day)

Status changed: **largely resolved, and the remainder is not a defect.**

Re-run against all 30 completed real students — the same metric, the same way: a concept
the counts call `strong` or `weak` that never appears in `strengths` or `gaps`.

| | at review time | re-measured |
|---|---|---|
| reports omitting a strong/weak concept | 13 of 22 (**59%**) | 5 of 30 (**17%**) |
| weak concepts omitted | several, incl. four on one student | **0** |
| reports with weak concepts and an empty `gaps` list | Gokul (4/20) | **0** |

The Gokul case — the one that mattered most, the lowest scorer with four weak concepts and
nothing in `gaps` — does not recur. No report now drops a weak concept.

### Why the remaining 17% is correct behaviour, not an omission

All five are the same shape: a **strong** concept left off a student who has five or six
of them, against a `strengths` list the schema caps at four. For example:

```
stu_6c627f5d   strengths listed = 4 (cap 4), strong concepts = 5
  listed   backing up a claim with evidence        3/4
  listed   picking the right data structure        3/4
  listed   understanding what a variable holds     3/4
  OMITTED  working out how long code takes         3/4
  listed   knowing when a loop or function stops   4/4
```

Every one is a high scorer whose strengths did not fit. `student_report.md` says *"at most
four entries in each list [...] listing everything is not a report"*, so this is the
design working. Counting it as a defect measures the cap, not the model.

What the original metric could not distinguish was **a weak concept silently dropped**
(a real failure — the student loses a diagnosis) from **a fifth strength not listed**
(intended — the report stays readable). Only the first is the bug, and it is now at zero.

### What fixed it

No single change aimed at this. The most likely contributors are the schema-shape work in
[bug 01](bug-01-report-truncation.md) (`_ENTRY`, the explicit field list) and
`enforce_verdicts()` moving misfiled entries into the right list rather than leaving them
out — on one of the five, the trail shows a 4-of-5 concept drafted under `gaps` and moved
to `strengths` in code, which is exactly the "entry exists but in the wrong place" case
that used to read as an omission.

The honest summary is that this was re-measured rather than fixed deliberately, and the
number moved. Recorded here rather than quietly dropped, because a bug written up as
confirmed should not simply disappear from the record.
