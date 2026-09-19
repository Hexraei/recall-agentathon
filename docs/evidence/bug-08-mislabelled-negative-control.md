# 08 — The negative control had a real pattern in it, twice

**Found by:** building the persistent-memory demo and running the real pipeline
against a group we had labelled "no pattern here."

## What happened

The memory demo needs two kinds of synthetic longitudinal identity: one whose
sittings share a misconception (the system should find it) and one whose
sittings do not (the system should refuse to claim one). The second is the
negative control, and it is the harder and more important half of the demo.

The first control was built on the rule *"four students whose wrong answers
spread across five different concepts."* The pipeline returned `recurring`.

That looked like a false positive. It was not. Two of the four had picked the
**identical wrong option on the identical question** — `cs_t1_q1`, distractor B,
*"treated the work as fixed; a loop that visits every item must do more work
when there are more items."* The agent cited exactly that pair and explained it
correctly. By the comparison prompt's own test — *would one explanation fix
both?* — it is recurrence.

So the rule was tightened: control members must share no wrong **question**.
The pipeline returned `recurring` again. Two sittings had missed two *different*
questions that rest on the same misconception about reference semantics —
`b = a` treated as making a copy, and `y = x` treated as a permanent link. The
citation was again accurate.

**Twice the system was right and our label was wrong.**

## Why it matters

The failure mode here is not in the code, it is in how a demo gets evaluated. A
negative control that secretly contains a real pattern produces a `recurring`
result that looks exactly like a false positive. Had we trusted the label over
the citation, we would have "fixed" a working comparison step to stop detecting
something real — and we would have stood in front of judges describing a
correct detection as a bug.

It also says something about the detection itself. The recurrence it found the
second time spans two different questions in two different topics with different
wording, sharing only an underlying misconception. That is precisely the
cross-topic pattern the system is for, and it found it in data assembled by
someone actively trying to construct an absence of patterns.

## The fix

The rule is now that a group advertised as a clean control shares no wrong
question *and* no wrong concept, and `validate()` in
`tools/build_memory_demo.py` enforces it at build time — a mislabelled group
fails the build rather than producing a confusing result at demo time.

The honest cost is recorded rather than hidden: with five concepts and 13
completed CS students, **no clean group of four exists in computer science at
all.** That group is published as a near-miss, labelled as such, and scored on a
different question — not "did it stay silent" but "when it made a claim, did it
cite evidence and hand the decision to a human." It did.

## The general lesson

Same shape as [bug-03](bug-03-biased-compare-prompt.md) and the
hallucinated-contradictions finding: the first plausible
explanation was wrong. Here the first plausible explanation was *"the model
over-claimed"* — the most comfortable conclusion available, because it blames
the model rather than the person who built the test. Reading the citation before
accepting that explanation is what made the difference.
