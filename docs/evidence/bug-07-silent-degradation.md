# Bug 07 — the fast provider was gone for the day and nothing said so

**Found:** 19 September 2026, investigating why a cohort run took 411s when an earlier one
took 209s.
**Status:** fixed (a warning, not a retry — the fallback itself was already correct),
regression-tested.
**Files:** `slice/llm.py`, `tests/test_quiz_app.py`

---

## What we were doing

Chasing tail latency. Runs over the same 30 real students varied between 209s and 411s
with no obvious cause, so we instrumented every HTTP call and counted statuses by provider.

## What we found

Across one 30-report run:

| | |
|---|---|
| model calls | 67 |
| **429s from Groq** | **37 (55%)** |
| 200s served by Groq (the fast primary) | **1** |
| 200s served by OpenRouter (the fallback) | **29** |

Twenty-nine of thirty reports were served by the slower secondary. The first assumption
was the per-minute token limit — Groq's free tier is 8,000 tokens/minute and a report
costs 2,000–3,700, so a back-to-back cohort run would collide with it by construction.

That assumption was wrong, and checking it mattered. Spacing reports **30 seconds apart** —
the real user path, one student finishing a quiz at a time — still produced a 429 on
*every single* request:

```
stu_010df982    7.7s  calls=[('groq', 429), ('openrouter', 200)]
stu_0916eacd    8.6s  calls=[('groq', 429), ('openrouter', 200)]
stu_0cf341b6    6.9s  calls=[('groq', 429), ('openrouter', 200)]
stu_0dfd0ce2    6.3s  calls=[('groq', 429), ('openrouter', 200)]
```

Reading the actual error body rather than the status code gave the answer:

```
Rate limit reached for model `qwen/qwen3.8-27b` ... on tokens per day (TPD):
Limit 200000, Used 198913, Requested 3133. Please try again in 14m43.872s
```

Not the per-minute limit. The **daily** one, 198,913 of 200,000 spent — by our own
measurement runs. `retry-after: 884`. The primary was gone for the rest of the day and
would stay gone.

## Why this is not a retry bug

`MAX_RATE_LIMIT_WAIT` is 20 seconds, and the code declined to wait 884. That is correct:
a quarter-hour wait is not a queue, it is an outage, and falling back is the right answer.
The fallback then served all 30 reports successfully.

**The degradation logic worked.** The system stayed up all day on a dead primary, which is
exactly what a named fallback on a different provider family exists to do.

The defect is that it did so **silently**. Nothing on screen distinguished

- "the fast provider is out of quota until tomorrow", from
- "the system is just a bit slow today".

Before a demo, those are very different facts, and the first one is discoverable only by
reading an error body nobody prints.

## The fix

`_warn_degraded()` prints once per model, to stderr, when a 429 arrives with a wait too
long to sit out. It reads the body to name the real cause — daily quota versus a
per-minute queue — and says the run is continuing on the fallback:

```
  [slice] qwen/qwen3.8-27b is rate limited for ~16 min (daily token quota spent -
  this will not clear until the quota resets).
  [slice] Falling back to the secondary model. Reports will still generate, more slowly.
```

Once per model, not per call: a 30-report run would otherwise print it thirty times. Not
an exception, because the run is still working and a fallback that quietly succeeds is the
point of having one.

## Guarding the regression

`test_a_spent_daily_quota_is_reported_once_not_silently_absorbed` — the warning fires,
names the daily quota specifically, does not repeat for the same model, and does not
claim "daily quota" for an ordinary per-minute limit.

## What we took from it

A status code is not a diagnosis. `429` covered two conditions — a ten-second queue and a
spent daily allowance — that call for opposite responses, and only the error *body*
distinguished them. The same lesson as bug 02's composing timeouts: every component behaved
correctly and the system still ended up somewhere nobody intended.

Worth recording separately: moving the checker into code
([bug 05](bug-05-checker-hallucinated-contradictions.md)) halved the model calls per report
from two to one, which halves quota consumption. A correctness fix turned out to be a
capacity fix as well.
