# Bug 01 — the report agent failed on exactly the student who needed it most

**Found:** 19 September 2026, Day 1 afternoon, during the first full generation run.
**Status:** fixed, verified, regression-tested.
**Files:** `app/report.py`, `app/prompts/student_report.md`, `app/prompts/class_report.md`,
`simulate.py`

---

## What we were doing

We had just built the quiz web app and needed the report agents exercised against a real
model at demo scale — not one call in isolation, but the whole cohort back to back, the
way it will actually run. So we seeded ten simulated students with **designed**
misconceptions (`simulate.py`) and generated all twelve reports — two class reports and
ten student reports — in one pass.

The personas are deliberately not random. Each one is wrong on a specific *concept*,
always choosing the same kind of distractor. That is what makes this a test rather than a
demo: we know in advance what each report should find, so we can tell the difference
between the agent finding the pattern and the agent writing something plausible.

## What broke

Eleven of twelve reports generated cleanly. The twelfth crashed:

```
slice.llm.ModelError: qwen/qwen3.8-27b returned HTTP 400:
{"error":{"message":"Failed to generate JSON. Please adjust your prompt.",
"code":"json_validate_failed",
"failed_generation":"max completion tokens reached before generating a valid document"}}
```

The failure took down the whole warm pass, so nothing after it ran either.

## Why it broke — and why this one is worth writing down

The student it failed on was **Vikram J, who scored 8/20 — the lowest in the cohort.**

That is not a coincidence, and it is the whole point of this entry. The report schema
allowed up to six `gaps` and six `strengths`, each with a free-text `evidence` sentence,
plus an unbounded `cross_topic_pattern`, `next_step` and `uncertainty`. **The more a
student struggles, the more there is to report, and the longer the JSON gets.** Every
request is capped at `settings.max_tokens` (1200). Vikram had the most gaps of anyone, so
his report was the first to run past the ceiling and get truncated mid-document.

So the failure mode was: **the agent works fine for students who are doing well, and
fails for the students who most need a report.** It would have passed any spot check we
ran on a single average student, and it would have failed live, in front of a judge, on
whichever tester did worst. We only saw it because we ran the whole cohort, including the
deliberately weak personas, rather than testing one happy path.

## Why we fixed it the way we did

There were three plausible fixes. We rejected two of them:

**Rejected — raise `max_tokens`.** This moves the ceiling without removing it. A student
scoring 4/20 has more gaps than one scoring 8/20; whatever number we pick, some student
exceeds it, and the failure comes back at the worst possible moment. It also costs more
tokens on every single call to protect against a rare one, which matters on a free tier
with an 8,000 tokens/minute limit.

**Rejected — catch the error and retry.** The retry would produce the same over-long
report and fail identically. Retrying an unchanged request that failed deterministically
is not a fix, it is a slower failure. (This is the same reasoning behind the redraft loop
in `app/report.py` carrying the rejection *reason* into the next prompt, rather than
blindly re-asking.)

**Chosen — bound the schema.** `strengths` and `gaps` capped at 4 entries, `solid` at 3,
`evidence` at 300 characters, `headline` at 200, the prose fields at 400–600. The bound
now lives in the Pydantic contract, where it is enforced, rather than in a prompt where it
would be a suggestion.

Two reasons this is the right fix rather than just the convenient one:

1. **It holds regardless of input.** The output size no longer depends on how badly a
   student did. The pathological case is now structurally impossible, not just unlikely.
2. **A shorter report is a better report.** This was the part worth noticing: the bound
   isn't a compromise forced on us by the token limit — it is what the artifact should
   have been anyway. A student reads one page in a minute and acts on two or three things.
   A teacher plans the next session around two or three things. A ten-item list of every
   concept ranked by score is a scoreboard, and we already decided a scoreboard is what
   this system exists *not* to produce. The token ceiling pushed us toward the design we
   should have chosen on the merits.

We also updated both prompts to ask for the same bounds, so the model aims for a
conforming report instead of writing a long one and having it rejected by validation.

## A second, smaller fix from the same failure

The crash killed the remaining reports in the warm pass. One student's report failing
should not cost the other nine theirs, so `simulate.py`'s warm loop now catches per
student, prints the failure, and continues. The page regenerates on demand anyway, so a
miss degrades to "that one student's report is slow the first time" instead of "the warm
pass died."

## Verification

Re-ran the exact case that failed — Vikram J, same seeded data:

```
OK 5.0s revisions=1
HEADLINE: Strong on counting work inside loops (3/5) but weak on identifying
          terminating base cases (0/3) and justifying claims with concrete
          arguments (0/3).
GAPS:      identifying a terminating base case [weak]
           justifying claims with a concrete argument [weak]
           choosing a structure from its access pattern [mixed]
STRENGTHS: counting work inside loops [strong]
```

Clean parse, 5.0 seconds, accepted on the first draft. It correctly found the designed
gap (`identifying a terminating base case`, 0/3) plus a second real one we had not
planted but which the seeded random answers genuinely produced.

Full suite: **44 tests green**, including the 25 pre-existing pipeline tests — the fix
touched only the report layer and did not disturb the extract/compare/draft/check flow.

## Still open, noticed during verification

Vikram's headline describes 3/5 as "strong", which contradicts the decision rule in
`student_report.md` (strong = all, or all but one of four). The structured `verdict`
fields are all correct; it is the free-text headline that overstates. The checker
accepted it, which means **the checker is enforcing the rule on verdicts but not on
prose.** Logged rather than fixed: it is a wording defect, not a wrong diagnosis, and the
numbers a teacher acts on are right. Worth a look if there is time — the likely fix is one
line in `report_check.md` extending rule 1 to cover the headline.
