# Jev evaluation 01 — the confidence floor is miscalibrated, but the signal underneath it looks real

**Found:** 19 September 2026, evening. Head-to-head test of Jev (the `jev-compare`
branch's decisions-API checker) against `main`'s current code-based report checker.
**Status:** diagnosed, not yet fixed. Written up before any change, on purpose — the
whole point of this note is to record what the data actually showed, including two
wrong guesses along the way, rather than the tidied-up version.
**Data:** 31 real students who completed the quiz today, both departments, drawn
directly from `webapp.db`. Not the seeded `demo.db` cohort.

---

## What was asked

Whether Jev is "better than what we have right now" — a direct comparison, not a
description of what Jev is designed to do.

## What was run

For each of 31 real, completed students: generate a real report draft with the same
model call `main`'s pipeline uses, then check that *same* draft with two engines —
`main`'s current code-based `check_claim_strength` (confirmed elsewhere as 30/30 clean
on this exact batch, filler eliminated) and Jev's `judge()` from the `jev-compare`
branch, unmodified. Same input to both, so any difference is the checker, not the
data.

## What came back

`main`'s checker: 31/31 accepted, as expected.

Jev: **29 of 31 flagged `below_floor` (unverified), 2 rejected outright, 0 clean
accepts**, at the branch's own default floor (`JEV_CONFIDENCE_FLOOR=0.60`).

Read as a bare number, that looks like Jev is either badly broken or absurdly
strict. It is neither — the confidence figure is being computed in a way that
cannot distinguish "confidently clean" from "confidently flawed," and that is the
real, first-order bug.

## First guess, wrong: claim-count compounding

`_report_bullets()` turns every field of a report into one numbered claim, and the
`false_somewhere` question asks "does at least one of these numbered claims have a
problem." With 8-10 claims per typical report, a small per-claim error rate should
compound into "yes, at least one is bad" fairly often just by the arithmetic of an
OR over many items — no bias required.

Checked it directly: plotted `noul_false` (Jev's raw answer, before the confidence
transform) against claim count per report. Claim counts sit in an 8-10 range across
almost the whole batch — not enough spread to explain `noul_false` values ranging
from 0.37 to 0.92. **This hypothesis is wrong**, and it is recorded here rather than
quietly dropped, because a fix built on it would have targeted the wrong mechanism.

## Second guess, tested and also wrong: a base-rate skew in the API itself

Sent Jev a synthetic, unambiguous control case — one claim, "the sky is blue,"
against a measured fact "sky_color: blue." If the `noul` question type or this
specific wording skews toward "true" regardless of content, an obviously clean
input should still come back elevated.

It came back at `noul_false = 0.18` — correctly, confidently clean. **This rules out
a systemic bias in the API or the question's wording in the abstract.** Whatever is
driving the real reports toward 0.6-0.9 is something about the real reports
themselves, not a broken instrument.

## What the data actually shows once those two are ruled out

Read the headlines at the two ends of the real distribution:

- **Lowest `noul_false` (Jev confident it's clean), 0.37-0.47:** "You got 18 of 20
  right, and the misses are all in one topic." "One mistake, in one topic, and a
  clean sweep on the rest."
- **Highest `noul_false` (Jev confident something is off), 0.78-0.92:** "You have a
  solid grasp of [X], but need to work on [Y] and [Z]." "One mistake, and it was a
  close call." "The misses are all in different places. That is a good sign: it
  means one tutorial will fix them all."

That last one is the clearest case. **"One tutorial will fix them all" is a
prediction about future performance** — not a number that can be checked against the
measured counts, because the counts describe what already happened, not what a
tutorial will do next. `main`'s checker cannot catch this: it compares stated
numbers against measured numbers, and there is no number in that sentence to
compare. Jev's own criteria explicitly names this category ("a claim about
something the counts cannot measure... future performance"), and it appears to be
doing exactly that job on real prose in a way `main`'s substring/arithmetic-focused
checker structurally cannot.

`main`'s own recent fix (documented elsewhere) specifically targeted absolute/filler
phrasing like "a clean sweep" for removal — and one of the reports still carrying
that exact phrase (`MONISH`, "a clean sweep on the rest") sits at the *low* end of
Jev's suspicion, not flagged. That is a genuine miss on Jev's part, in the other
direction: it did not catch a phrase the team has already identified as filler
worth removing. Neither checker is strictly better across the board; they appear
to be sensitive to different things.

## What this means, stated as plainly as the data supports

- **Not proven:** that Jev is more accurate than `main`'s checker overall. Two
  confirmed-good catches (Harshadraam D, Sutharshan K, both flagged for real,
  independently-verifiable issues) is evidence Jev can find something `main`
  misses — it is not evidence of a general accuracy advantage across 31 reports,
  most of which `main` also correctly called clean.
- **Not proven:** that Jev is unreliable or biased. The control test clears it of a
  base-rate skew, and the two real catches were not false positives.
- **Confirmed:** the confidence-floor mechanism as built (`|2*(noul-0.5)|` at a 0.60
  floor) cannot ship as-is. It flags 29 of 31 real, independently-verified-clean
  reports as unverified, which in the actual web app renders a warning banner on
  almost every report — not a selective quality signal, noise at that setting.
- **Confirmed:** Jev appears to be judging a genuinely different, harder thing than
  `main`'s checker — unmeasurable/predictive claims in natural prose, not exact
  numeric contradiction — and that is worth keeping, not discarding, once the floor
  or the criteria are retuned.

## What has not been done yet

- The floor has not been retuned or removed. 0.60 was the branch's original
  default; nothing here justifies picking a specific replacement number without
  measuring it the same way.
- Whether "one tutorial will fix them all"-style predictive language is common
  enough across the whole cohort to be worth a dedicated, code-side check (the same
  move that fixed the clean-sweep and repeated-sentence problems in `main`) has not
  been checked.
- Jev has not been re-run against any of the specific fixes `main`'s checker
  received today (filler removal, repeated-sentence rejection) — this evaluation
  used the reports as generated by today's real students, some of which may
  reflect an earlier version of the writer prompt.
