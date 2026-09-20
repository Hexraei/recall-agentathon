# Bug 05 — the checker rejected true sentences, using the numbers that proved them

**Found:** 19 September 2026, measuring the report loop over the seeded cohort.
**Status:** fixed, verified, regression-tested.
**Files:** `app/report.py`, `slice/llm.py`, `app/prompts/report_check.md` (deleted),
`tests/test_quiz_app.py`

---

## What we were doing

The report agent drafts, then a second model call checks the draft for false claims
against the measured counts, and rejects with a reason if it finds one. We measured the
whole loop the way it actually runs: all ten seeded students across both departments,
`force=True`, counting drafts, `_unverified` flags and crashes.

## What broke

Out of ten reports:

| | |
|---|---|
| hard-crashed with `SchemaFailure` | **2** |
| hit `MAX_DRAFTS` and shipped flagged `_unverified` | **5 of the 8 survivors** |
| came back clean | **3** |

Seven of ten reports were failing, and the dominant cause was the checker. These are the
rejection reasons, verbatim from `demo.db`:

> The sentence 'All the answers here were right.' is false. The counts show that the
> concept 'reasoning about singularities and degeneracy' had 3 correct answers out of 3
> asked [...]

3 correct out of 3 asked. The sentence is **true**, and the checker quoted the very
numbers that prove it. Rejected twice.

> The headline says 'You got 8 of 20 questions right.' but the counts show 8 correct out
> of 20 asked.

Identical numbers, presented as a contradiction. Rejected twice, verbatim.

> The headline says 'one topic was clean', but the counts show that 'Memory & State' was
> the only topic with no mistakes. The other topics all had mistakes.

A restatement of the supporting fact, offered as a refutation.

## Why it broke

Not a wording problem. Three previous rounds of tightening `report_check.md` changed
*which* false rejections happened, never *whether* they did.

The checker was asked to hold a sentence and a JSON blob side by side and decide whether
one contradicts the other. That is exact structural comparison, and it is the same
capability gap this codebase had already routed around three times:

| Moved to code | Why | Held up? |
|---|---|---|
| `verdict_for()` | writer said `weak` for 4-of-5; checker "corrected" 0-of-3 to `strong` | yes |
| `enforce_pattern()` | checker rejected the planted 4-topic pattern on nearly every phrasing | yes |
| `check_citations()` | a model asked whether its own citation is real says yes | yes |

Every judgement call moved into code stayed fixed. Every one left with a model kept
failing. `claim_strength` was the last one still being asked of a model, and it failed
the same way.

The second failure was separate and hiding behind the first. The two `SchemaFailure`
crashes were **not** the truncation of [bug 01](bug-01-report-truncation.md) recurring —
every reply finished cleanly, `finish_reason` was `"stop"`, and the JSON was complete and
well formed. Instrumenting the exchange showed the real chain:

1. A 429 on Groq sends the request to the OpenRouter fallback.
2. The fallback is handed `{"type": "json_object"}`, a loose contract with **no field
   bounds**, because the strict schema is only sent to Groq models.
3. Mistral writes a 192-character `evidence` against a 160-character cap. Pydantic
   rejects it.
4. The repair pass re-sends to the same model **at temperature 0** and gets a
   byte-identical 1843-character reply. Same failure.
5. `SchemaFailure` — a student's entire report lost to 32 characters of one sentence.

## The fix

**The checker is code, not a model call.** `check_claim_strength()` verifies the three
things that are actually checkable: a headline's score against `score`, a clean-sweep
claim against that concept's `correct`/`asked`, and language that ranks a student or
describes their character. `report_check.md` is deleted and `build_check_messages()` is
gone. A clean report now costs one model call instead of two.

**The repair pass can differ from what it is repairing.** It sends the strict schema
wherever the provider accepts one, and runs at temperature 0.3 — at 0 it was a guaranteed
replay of the failing answer.

**A length overrun is trimmed, not fatal.** `_trim_to_bounds()` cuts an over-long string
back to its declared bound at a word boundary, ending in a full stop, so it still reads
as a sentence on a student's results page. Only length is salvaged: a missing field, a
wrong type or a bad enum still fails, because those change what the report *says* where a
trimmed sentence only says it shorter.

## What this fix got wrong first, twice

Worth recording, because both were the original bug reappearing in the fix.

The first cut matched bare substrings. On a 4-of-5 concept it rejected:

> The one miss assumed every append reallocates; amortised growth means copies happen
> rarely, not every time.

A sentence that *explicitly admits the miss*, failed on `"every time"` — a phrase
describing the misconception, not the student. The second cut rejected a correct robotics
sentence about a Jacobian being `rank-deficient`, because the comparison list contained
the bare word `"rank"`.

Both are the checker-model failure reproduced in code: a false rejection of a true
sentence, on data that supports it. The rule now requires phrases that cannot fit inside
a technical term, stands down on any sentence that names a miss, and knows that "most
students" is descriptive on a class report and a ranking on a student one.

Neither would have been caught by the unit tests. Both came from running the cohort.

## After

Same measurement, same method, run twice:

| | before | after |
|---|---|---|
| clean | 3 | **10** |
| `_unverified` | 5 | **0** |
| crashed | 2 | **0** |
| drafts per report | 1–2, mostly 2 | **1** |
| wall clock | 318s | **79–99s** |

Both class reports also clean. Every report now passes on its first draft, which is what
you would expect once the checker stopped inventing objections to answer.

## Guarding the regression

In `tests/test_quiz_app.py`:

- `test_true_sentences_the_checker_model_used_to_reject_are_accepted` — the three real
  false rejections from `demo.db`, pinned.
- `test_a_genuinely_false_claim_is_still_rejected` — the inverse, so the fix cannot
  degrade into accepting everything.
- `test_a_sentence_that_admits_its_miss_is_not_a_clean_sweep_claim` and
  `test_domain_vocabulary_is_not_mistaken_for_a_ranking_or_an_insult` — the two false
  positives the fix itself caused.
- `test_an_over_long_field_is_trimmed_rather_than_losing_the_report` and
  `test_trimming_does_not_rescue_a_structurally_wrong_reply` — salvage recovers length,
  and only length.

## What we took from it

Two things.

A model that is handed the right numbers can still fail to compare them, and it will
explain its error using the correct figures. "Give it the facts" is not sufficient; the
comparison itself has to be mechanical or it is not reliable.

And the check kept its shape while changing its substrate. A rejection still carries a
reason, still routes back to `DRAFTING`, still shows up in the trail — the back-edge a
judge watches is intact. What changed is that the thing deciding is now right every time
and can be unit-tested.
