# Bug 03 — the comparison step was wrong nine times out of ten, and we had written the bias ourselves

**Found:** 19 September 2026, Day 1 morning.
**Status:** fixed, measured before and after, regression-tested.
**Files:** `app/prompts/compare.md`, `tests/test_flow.py`

---

## What we were doing

Running the two-encounter demo (`live.py --full`) repeatedly against the real model to
check it was stable before showing anyone. The system is supposed to notice that Mira's
second submission repeats the misconception from her first, and label the comparison
`recurring`.

It did — sometimes. Other runs came back `similar`, or `improving`, on **identical input**.

## What we did first, and why it was the right order

Our first instinct was "the model is flaky, try a different model." We did not act on it.
Instead we wrote a throwaway diagnostic that ran the comparison step alone, on fixed
input, ten times, and counted the labels.

That distinction mattered: if we had swapped models and the numbers had improved by
chance, we would have shipped a system that was still wrong and drawn exactly the wrong
lesson about why it worked.

**Measured, before any change: 9 of 10 trials returned `similar` where `recurring` was
correct.**

That is not flakiness. A model that is guessing gives you a spread; a model that is wrong
nine times out of ten in the *same direction* is being told to be.

## Why it broke

We read our own prompt. `app/prompts/compare.md` contained, in our own words:

> when the evidence supports `similar` and you want to write `recurring`, write `similar`

We had written that earlier, deliberately, guarding against false positives — the system
telling a professor a student has a recurring misconception when they do not. That is a
real risk and worth guarding against. But the guard was **a mood, not a rule**: it told
the model which answer to prefer without telling it how to decide, so it preferred that
answer nearly always, including on the cases the entire system exists to catch.

The deeper mistake was the shape of the instruction. We had tried to encode a judgement
call as a *disposition* ("lean toward the cautious answer") rather than as a *procedure*
("here is how to tell the two apart"). A disposition has no floor.

## The fix, and why this shape

Rewrote `compare.md` as an **ordered decision procedure** with a concrete test at the
branch point, rather than a preference:

1. `not_enough_evidence` if there is no prior history at all.
2. `improving` only with quoted evidence of correcting the *same* prior difficulty.
3. `recurring` if **one explanation would fix both** — the operative test.
4. Otherwise `similar`.

Plus two worked examples in the prompt: Mira's case (should be `recurring`) and Arun's
(should be `similar`), so the boundary is shown rather than described.

The false-positive guard did not go away — it moved. It now lives in step 3's test and in
a **code-side rule** in `app/flow.py` that downgrades `recurring` to `not_enough_evidence`
whenever the evidence spans fewer than `RECURRENCE_NEEDS_ATTEMPTS` assignments, whatever
the model says. That rule is a claim about teaching, so it belongs in code where it can be
argued with and tested, not in a prompt where it is a suggestion.

## Verification — and the part that mattered most

Re-measured on the same fixed input:

| case | before | after |
|---|---|---|
| Mira (correct answer: `recurring`) | 1/10 correct | **8/8 correct** |
| Arun (correct answer: `similar`) — negative control | 8/8 correct | **8/8 correct** |

**The negative control is the number we cared about.** Any change that makes the system
say `recurring` more often will improve the Mira row — including simply telling it to
always say `recurring`. That would be a worse system wearing a better score. Arun is a
student with a real but *different* history, and holding 8/8 there is what shows the fix
taught the step to **discriminate**, rather than just shifting its bias in the direction
we happened to want this week.

This is why our negative control is a student with a genuinely different misconception
rather than a student with no history: a blank-history student returning
`not_enough_evidence` only proves the system can count to zero.

## Guarding the regression

Two tests in `tests/test_flow.py` read the prompt file directly:

- `test_compare_prompt_does_not_bias_toward_hedging` — fails if the preference language
  comes back.
- `test_compare_prompt_states_a_decision_rule` — fails if the ordered procedure is
  removed.

Testing a prompt's *text* is unusual and we thought about whether it was worth it. It is,
here: the defect was not in code and no behavioural test would have located it, because
the behaviour was individually plausible every single time. Only the aggregate over ten
trials showed it, and we cannot run ten live trials in CI.

## What we took from it

The bug was ours, not the model's, and we found it only because we measured before
concluding. The general form — *an instruction that expresses a preference instead of a
procedure will be followed to its limit* — is now something we check for when writing any
prompt, and it is why the report prompts added later
([bug 01](bug-01-report-truncation.md)) are written as ordered rules with explicit
thresholds rather than as guidance about tone.
