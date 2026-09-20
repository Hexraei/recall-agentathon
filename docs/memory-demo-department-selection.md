# Why robotics got the clean-pattern demo and CS got the erratic one

The original four memory-demo identities (`mem_robotics_a/b`, `mem_cs_a/b`)
each hand-picked students *within* one department to build a clean group and a
messy group side by side. That is defensible, but it invites a fair question:
did the students get sorted into "clean" and "messy" to produce the answer we
wanted?

The two department-level identities (`mem_robotics_clean_dept`,
`mem_cs_erratic_dept`) answer that differently: **the department was chosen
first, by measuring the whole real cohort, and the category followed from the
measurement** rather than the other way around.

## The measurement

Pulled directly from `webapp.db`, 19 completed robotics students and 14
completed computer-science students, counting how many students got each
concept wrong at least once:

**Robotics** — one concept stands well above the rest:

```
13/19  working out where the robot ends up
 9/19  accounting for weight and force
 9/19  matching a fix to what went wrong
 8/19  backing a claim with a measurement
 8/19  choosing a method for the job
 6/19  combining movements in the right order
```

68% of the department shares one real difficulty. Checked further: of those
13, **7 chose the identical wrong option** (`B`) on the identical question
(`rb_t1_q2`) for the identical stated reason — "assumed the forward
calculation simply reverses; it does not." That is not "many students got it
wrong for different reasons" — it is one specific, real, shared
misunderstanding, independently arrived at by 7 different people.

**Computer science** — no concept stands out at all:

```
10/14  backing up a claim with evidence
10/14  picking the right data structure
10/14  understanding what a variable holds
 5/14  working out how long code takes
 3/14  knowing when a loop or function stops
```

Three different concepts, tied at exactly 10 of 14 students each. There is no
single answer to "what does this class struggle with" — three candidates,
none more real than the others.

## What that measurement decided

- **Robotics → the clean-pattern demo** (`mem_robotics_clean_dept`, "Devika
  R."). The 7 students who shared the identical wrong answer became the 7
  sittings. Nothing about which of the 7 to include was a judgement call —
  they were the entire set that matched.
- **Computer science → the erratic demo** (`mem_cs_erratic_dept`, "Aravind
  S."). Six members picked for genuinely *different* concept profiles (from
  one wrong concept each to four), specifically to avoid accidentally
  reconstructing one of CS's three tied candidates inside a supposedly messy
  group. Checked afterward for real overlap: the six members share individual
  wrong *questions* pairwise seven separate times, scattered across seven
  different question pairs, with no two sittings ever sharing the same pair
  twice. That scatter — real, measured, not manufactured absence of
  overlap — is what "erratic" means here.

## What actually happened when the pipeline ran

Both groups ran through the real shipping pipeline (`app/flow.py`, unmodified,
via `tools/run_memory_demo.py`), not a mock.

**`mem_robotics_clean_dept`**: `not_enough_evidence → recurring → recurring →
recurring → recurring → recurring → recurring`. Every sitting from the second
onward — 6 out of 6 that had history to read — correctly found the
recurrence, all the way through a seventh sitting reading six prior sittings'
worth of real evidence.

**`mem_cs_erratic_dept`**: `not_enough_evidence → improving → similar →
similar → similar → recurring`. Real variety across four different labels.
The one time it did claim `recurring` (the sixth and final sitting), it cited
its evidence and the run paused for a professor rather than auto-confirming —
the human-in-the-loop behaviour firing correctly even in the department that
was expected to be ambiguous.

## A real bug this surfaced, fixed along the way

Building the 7-sitting robotics chain, sitting 6 failed outright:

```
HTTP 413: Request too large for model qwen/qwen3.8-27b ... input tokens per
minute (ITPM): Limit 7000, Requested 7315
```

The comparison step reading 5 prior sittings' worth of real history produced
a prompt that exceeded Groq's per-minute input token cap. `slice/llm.py`'s
fallback logic triggered on `429/500/502/503` and one specific `400` shape,
but not on `413` — so instead of falling back to the secondary model, the
whole run failed. This had never surfaced before because no existing group
had more than 4 sittings, and 3 prior sittings' worth of history had never
been enough to hit the limit.

Fixed by adding `413` to the set of statuses that trigger a fallback: the
request is not oversized in any absolute sense, only relative to a quota that
resets every minute, so it is exactly the kind of transient condition a
different provider should absorb. Re-ran after the fix: 6 of 6 clean, no
further failures.

This is also the reason `mem_robotics_clean_dept` has 7 sittings while the
original groups had 3-4 — the point of building a whole-department group at
all was to see whether the detection held up over a longer, more realistic
chain, and it would not have been tested at that length without hitting (and
fixing) this limit.

## What this does not claim

- **The category still had to be checked, not assumed.** A whole department
  sharing a concept does not by itself guarantee the model will call it
  `recurring`; it had to actually run and be read. It did, 6/6.
- **CS's erratic result is not "the system failed."** `similar` on real
  overlapping-but-different mistakes, and one `recurring` claim that
  correctly paused for a human, are both the system working as designed — see
  `FLUTTER_CONTEXT.md`'s "Showing it fail" section for how to present this
  live without letting it read as a bug.
- **This does not replace the original four identities.** They stay in
  `docs/memory-demo-manifest.json` and `docs/memory-demo-results.json`
  alongside the two new ones — six identities in total, all real answers, all
  real model calls.
