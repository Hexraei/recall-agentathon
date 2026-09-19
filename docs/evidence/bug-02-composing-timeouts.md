# Bug 02 — three correct timeouts composed into a forty-minute hang

**Found:** 19 September 2026, Day 1 afternoon, during a real network outage mid-run.
**Status:** fixed, regression-tested.
**Files:** `app/report.py` (`DEADLINE_SECONDS`), `simulate.py`

---

## What we were doing

Re-running the full cohort generation after fixing [bug 01](bug-01-report-truncation.md),
to confirm all twelve reports now complete. Partway through, the venue's internet dropped.

We are documenting this one *because* it was an accident. We did not plan a network-outage
test, and we would not have thought to write one — which is exactly why the failure it
exposed was still in the code.

## What broke

The run kept going, but the log showed this:

```
  class robotics           68.2s  3 draft(s)
  Anita G                  60.8s  2 draft(s)
  Priya K                  60.0s  3 draft(s)
  Rahul M                2370.8s  FAILED: ModelError: Both models unreachable
  Suresh B                  0.0s  FAILED: ModelError: Both models unreachable
```

**2,370 seconds — thirty-nine minutes — on a single report before it gave up.**

## Why it broke

This is the interesting part, and the reason it is worth a write-up rather than a line in
a changelog: **every individual timeout in that path was set correctly.** Nothing was
misconfigured. There was no bug in any one component.

- `slice/llm.py` uses a 120-second HTTP timeout per request. Reasonable.
- On a network error it falls through to the fallback provider. Correct — that is what a
  fallback is for.
- On a 429 it waits and retries once. Correct, and deliberate: a rate limit is a queue,
  not an outage ([see `MAX_RATE_LIMIT_WAIT`](../../slice/llm.py)).
- `report.py` may draft up to `MAX_DRAFTS = 3` times when the checker rejects.

With DNS resolution itself hanging, each of those layers did its job and waited its
allotted time. **They multiplied.** Three drafts, each with a check, each trying a primary
and a fallback, each waiting up to two minutes, plus retry backoff — and the product is
forty minutes.

The general lesson we took from it: *a bounded component composed with another bounded
component is not automatically bounded at a useful number.* Each layer knew its own limit
and none of them knew the total.

## Why the existing fences did not catch it

We already had two counters, and it is worth being precise about why neither helped,
because "we had a limit" was our first assumption and it was wrong:

- **`MAX_DRAFTS` did not help.** It bounds how many times the loop *iterates*. All that
  time was spent *inside* a single iteration's call chain, so the loop counter never
  advanced far enough to trip.
- **The token budget did not help.** It counts tokens *reported by completed responses*.
  A request that never returns reports nothing, so a run that hangs forever spends zero
  budget and looks, to the fence, completely idle.

Both fences were measuring the right things for the failures they were designed for. This
failure was a different axis, and it needed its own counter.

## The fix, and why this shape

Added `DEADLINE_SECONDS = 90.0` in `app/report.py`: a wall-clock fence on the whole
report, checked between drafts.

Three specific decisions inside that:

**A third separate counter, not a shared one.** The kit's own design rule — and the one
we already follow for the spend-vs-revision split in `app/flow.py` — is that two limits
fencing two different failures must never share a counter, because then one silently
consumes the other's budget. Time, drafts and tokens are three different failures, so
they get three counters.

**Checked before a draft, not after.** The point is to refuse to *start* work that will
finish too late to be useful. Checking afterward would let a fourth draft run to
completion before noticing the deadline had passed twenty minutes earlier.

**Ships the last draft rather than raising.** When the deadline hits, the report goes out
with `_unverified` set, and the web page renders that as a visible "Unverified" banner. A
teacher is better served by a report that admits it was not checked than by an error page
— but it must never be mistaken for one that passed. This mirrors what we already do when
`MAX_DRAFTS` is exhausted.

We did **not** lower the per-request HTTP timeout. 120 seconds is correct for a single
call on a congested free tier, and cutting it would make ordinary slow-but-working calls
fail. The problem was never any one request's patience; it was that nothing owned the
total.

## A second fix from the same failure

`simulate.py`'s warm loop caught the per-student failure and continued — which is why
Suresh's line appears at all rather than the run dying at Rahul. That part worked, and it
worked because of a fix we had made an hour earlier for bug 01.

But the class report was still unguarded: a class-level failure would have killed the
whole pass. Now wrapped the same way.

## Verification

`test_a_slow_report_stops_at_the_deadline_and_ships_what_it_has` in
`tests/test_quiz_app.py` drives a fake clock past the deadline after the first draft and
asserts the loop stops at one revision, flags `_unverified`, and still returns a usable
report rather than raising.

Getting that test to actually fail-then-pass took three attempts, which is itself worth
noting: the first two versions patched the clock by counting calls, and the count was
consumed by unrelated `time.time()` calls in the store's own timestamping. The working
version keys off the scripted model call instead of a call count. **A test that passes for
the wrong reason is worse than no test**, so it was worth confirming it failed against the
unfixed code first.

Full suite: **45 tests green.**

## What we would do differently

We found this by accident. The honest conclusion is that we have no deliberate test for
degraded-network behaviour, and every timeout in the system is still only verified under
a working connection. If there is time on Day 2, the test worth writing is a fault
injection at the `httpx` boundary — not more unit tests of the fences we now know about.
