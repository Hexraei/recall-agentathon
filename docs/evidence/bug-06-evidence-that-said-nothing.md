# Bug 06 — two thirds of reports repeated themselves, and half the sentences said nothing

**Found:** 19 September 2026, measuring report *quality* over the 30 real students in
`webapp.db` after the correctness work in [bug 05](bug-05-checker-hallucinated-contradictions.md).
**Status:** fixed, verified on the same 30, regression-tested.
**Files:** `app/report.py`, `app/prompts/student_report.md`, `app/prompts/class_report.md`,
`webapp.py`, `tests/test_quiz_app.py`

---

## What we were doing

Every check in this system asks *is the report FALSE?* All 30 real reports passed. So we
asked a different question — *is it worth reading?* — and counted what a student actually
sees.

## What broke

Across 30 real reports and 150 entries:

| | |
|---|---|
| reports repeating a sentence across entries | **20 (67%)** |
| duplicate occurrences | **38** |
| filler sentences ("You got all of these right") | **55** |
| clean concepts carrying prose | **74** |

One real report, verbatim:

> **Gaps**
> - *accounting for weight and force* — "The misses both missed a continuous effect: gravity pulling on a held position, and the factor applying along both width and height."
> - *working out where the robot ends up* — "The misses both missed a continuous effect: gravity pulling on a held position, and the factor applying along both width and height."
> - *backing a claim with a measurement* — "The misses both missed a continuous effect: gravity pulling on a held position, and the factor applying along both width and height."

The same sentence under three different headings. It is a fair description of the first
concept, a stretch for the second, and simply wrong about the third — you cannot describe
a measurement-citing mistake as "gravity pulling on a held position".

## Why it broke

Two causes, and they are different.

**The filler.** `evidence` is defined as *what the wrong answers have in common*. A
concept with no wrong answers has no such sentence — but the field was required, so the
model had to write something. It wrote the only true thing available: "You got all of
these right", 55 times, directly beside a score already reading 3/3. A required field
with nothing to put in it gets filled with noise.

**The duplication.** Having found one pattern, the model reused the sentence rather than
reading each concept's own `wrong_answers`. Nothing checked for it, because every existing
check asks whether a sentence is false, and a sentence that is true of *one* concept does
not look false in isolation.

Both were invisible to the correctness checks. A report can be entirely true and still
tell a student nothing.

## The fix

Two changes, deliberately of different kinds — the split is the interesting part.

**`evidence` is now optional, and cleared in code when there is nothing to say.**
`strip_empty_evidence()` blanks the field on any concept with `wrong_answer_count == 0`.
Removed rather than sent back, on the same reasoning as `enforce_pattern()`: no rewrite
turns an absent mistake into an observation about one, so a redraft would spend a round
trip to produce the same filler. The score beside the entry already carries the fact.

**A sentence reused across two concepts is rejected and redrafted.**
`check_distinct_evidence()` sends it back with both concept names. This one *is* worth a
redraft, because unlike the filler case the mistakes genuinely are there to be described —
the model simply described them once and pasted the result. That is something a rewrite
can fix, and measurably does.

`webapp.py` omits the paragraph entirely for an empty sentence rather than rendering a
blank one.

## After

Same 30 students, same method:

| | before | after |
|---|---|---|
| reports repeating a sentence | 20 (67%) | **0** |
| duplicate occurrences | 38 | **0** |
| filler sentences | 55 | **0** |
| clean concepts carrying prose | 74 | **0** |
| reports clean / unverified / crashed | 30 / 0 / 0 | **30 / 0 / 0** |

The same student's report, regenerated:

> **Strengths**
> - *choosing a method for the job* — (no sentence; the score says it)
>
> **Gaps**
> - *accounting for weight and force* — "The misses treated a held position as free, and applied a factor once where it applies twice."
> - *working out where the robot ends up* — "The misses treated a one-way calculation as reversible, and a distance as fixing a position."
> - *backing a claim with a measurement* — "The misses cited values for a different machine, and named a possible cause in place of the observation."

Three distinct readings of three different concepts, where there had been one sentence
three times.

## Guarding the regression

In `tests/test_quiz_app.py`:

- `test_a_concept_with_no_mistakes_carries_no_sentence` — filler is cleared, and a concept
  that *does* have mistakes keeps its sentence.
- `test_one_sentence_may_not_stand_in_for_two_concepts` — duplicates rejected, distinct
  sentences pass, and two *empty* sentences are not duplicates.
- `test_the_results_page_omits_an_empty_sentence_rather_than_printing_a_blank`.

## What we took from it

Correctness checks do not measure usefulness, and passing every one of them told us
nothing about whether the reports were any good. We only found this by asking what a
student would see rather than whether the system agreed with itself.

The second thing is the split between the two fixes. "Move it to code" has been right
every time in this codebase, but *which* code matters: something a rewrite cannot fix gets
removed silently, and something a rewrite can fix gets sent back with a reason. The filler
was the first kind and the duplication the second, and treating either as the other would
have cost a round trip or shipped the defect.

---

## Two smaller things found in the same pass

### The trail hid the half of the system that is code

`_trail_html()` in `webapp.py` rendered `draft` and `check` steps and sent everything else
down the `check` branch. The `correct` step — where code recomputes a verdict from the
counts, moves a misfiled entry, drops an unsupported pattern or clears filler — came out as
a bare `check r2 →` with nothing after it.

That is both wrong and unfortunate, because it is the most interesting line in the trail.
The whole argument of this codebase is that arithmetic belongs in code and judgement
belongs in the model, and the trail was showing only the model's half. Now:

```
draft  r1  → You got 16 of 20 right, and the misses are all in two topics.
check  r1  → rejected  (citation) Names concepts with no answered questions behind them...
draft  r2  → You got 16 of 20 right, and the misses are all in two topics.
code   r2  → backing up a claim with evidence: weak -> strong (4 of 4), moved gaps -> strengths
code   r2  → backing up a claim with evidence: cleared evidence (no wrong answers)
check  r2  → accepted
```

Pinned by `test_the_trail_shows_what_code_corrected_not_a_blank_check_line`, which also
asserts no check line renders without a verdict.

### MAX_DRAFTS = 2 was right for a reason that had expired

The docstring justified 2 on the grounds that *"the checker that rejected draft 2 rejected
draft 3 as well, usually on a different marginal objection"*. That checker was a model, and
those objections were mostly hallucinated — the subject of
[bug 05](bug-05-checker-hallucinated-contradictions.md). The reasoning had to be redone
rather than inherited.

Re-measured over 96 report runs under the current code-based checks:

| | |
|---|---|
| accepted the first draft | **95** |
| rejected, redrafted, accepted | **1** |
| spent the budget without a clean draft | **0** |

Two is still correct, for the opposite reason to the one recorded: not "a third draft would
not help" but "a second one already finishes the job". The docstring now says so, with the
numbers.

---

## A third thing, found by the fix's own re-measurement

The first run after the fix came back with one report still showing a duplicated sentence —
1 of 30, where the metric had been 20 of 30. Reading it showed something the original
metric had been hiding all along:

```
[strengths] knowing when a loop or function stops   The one miss expected the condition...
[strengths] picking the right data structure        The one miss attributed the speed...
[strengths] understanding what a variable holds     The one miss treated `b = a` as...
[strengths] working out how long code takes         The one miss gave the average...
[strengths] knowing when a loop or function stops   The one miss expected the condition...
[strengths] working out how long code takes         The one miss gave the average...
```

Two concepts listed **twice**, each with its own sentence repeated. Not a duplicated
sentence across different concepts — a duplicated *entry*.

And not the model's doing. The trail shows the draft was correct: four strengths and two
gaps, every concept distinct within its own list. What happened next was ours:

```
corrections:
  knowing when a loop or function stops: strong (3 of 4), moved gaps -> strengths
  working out how long code takes:       strong (3 of 4), moved gaps -> strengths
```

`enforce_verdicts()` correctly decided both gaps had earned `strong`, and appended them to
`strengths` — which already named both concepts. The writer had listed each concept in both
lists, which nothing forbade, and the move turned that into a visible stutter.

So the check that found this was measuring one thing (repeated sentences) and caught a
different, older defect underneath it. `enforce_verdicts()` now refuses to append a concept
the destination already names, and `check_distinct_evidence()` rejects any concept listed
twice anywhere in the report.

| | before | after fix | after this second fix |
|---|---|---|---|
| reports with a duplicated sentence | 20 (67%) | 1 (3%) | **0** |

Pinned by `test_moving_an_entry_on_verdict_does_not_duplicate_a_concept` and
`test_a_concept_listed_twice_is_rejected`.

The general lesson is the one this directory keeps relearning: a fix is not done when the
code is written, it is done when the same measurement is run again. This one found a bug
that predated the fix and would have survived it.
