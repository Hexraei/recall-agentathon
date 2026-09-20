# CONTEXT.md — Why Jev judgement beats code-based flagging, with real test cases

**Branch:** `jev-compare` · **Date:** 20 Sept 2026 · **Companion docs:** `JEV_CONTEXT.md`
(branch story), `SMOKE_RESULTS.md` (full smoke output, 9-demo tutorial).

This file answers one question a judge will ask: **you already have deterministic
code checks — why is a second, model-based judgement layer better?** It also
stays honest about where code wins, because the honest version is the
convincing one.

---

## The short answer

Code checks can only catch lies someone predicted in advance; Jev reads the
claim and catches the ones nobody predicted — and when it *can't* be sure, it
says so with a number, so a person decides instead of a coin flip.

---

## What each layer actually is

| | Code-based check | Jev judgement |
|---|---|---|
| **How it decides** | String/regex/count rules written in advance | Reads the claim against the facts; produces noul (probability of falsehood) + confidence |
| **Catches** | Exactly the enumerated lie-patterns | Anything it reads as false/unmeasurable/ad-hominem — including patterns nobody enumerated |
| **Confidence** | Binary: matched or didn't | Calibrated: 0.98 sure, 0.26 not sure |
| **Honesty about limits** | None — it is always equally sure | The number itself says "I'm not sure" |
| **Cost** | Free, deterministic, instant | A network call + tokens; can fail (so it falls back visibly) |

Neither replaces the other. The architecture is layered: code does the
clerical work it is provably good at; Jev does the reading-comprehension
judgement that remains; the human takes what is left when the machine is unsure.

---

## Real runtime test cases (all numbers verbatim from SMOKE_RESULTS.md)

### Case 1 — the lie a rulebook could also catch, but only because it was lucky
Report headline: *"answered every single question correctly — a perfect score."*
Facts: the student scored **19/20**.

- A code check catches this **only if** someone authored a pattern like
  `"all/perfect/every" + score < max`. Hexraei's team did author exactly that
  (`check_claim_strength()`) — after a *different* checker first failed. But
  the same student could write "I only lost a mark on the trickiest one," or
  "my loops are all correct," and every variant needs a fresh regex.
- Jev, asked "is any claim here false?", returns **noul=0.99, confidence=0.98 →
  rejected** — live, reproduced across independent re-runs. It needed no
  pattern enumerated in advance: it read the claim against the fact table.

### Case 2 — the lie-code-misses class
Same 19/20 student. Now the report says: *"The loop-counting gap seems minor
next to the rest of the work"* — when the fact table shows loop counting was
**the only gap, 0/5 correct**. No clean-sweep keyword, headline matches the
score exactly, every predicate a rule could grep for is true. A code check passes it.
Jev's job is exactly this: is the claim *proportioned* to what the numbers say?
(Its `bad_claim_noul` question runs per-claim, not per-report, which is what
makes understatement-by-implication visible.) The chat-path era measured this:
the generative checker failed 7 of 10 reports — but the *absence* of a reading
checker means those 7 failure-modes simply ship silently.

### Case 3 — calibrated uncertainty, the thing a rulebook structurally cannot do
Three consecutive runs on a **clean, fact-conformant** report:
noul/conf = **0.55/0.10, 0.43/0.14, 0.37/0.26**. All accepted — but all below
the 0.60 floor → shipped flagged `_unverified`:
`"Jev confidence 0.26 below 0.60; report shipped unverified."`
A code check has no channel for "I checked and I'm not certain"; it either
flags nothing or flags everything. The floor turns that graded uncertainty into
a *routing decision* the professor sees — the professor-review trail is
therefore populated by real doubt, not by a boolean.

### Case 4 — comparison is reading comprehension, not arithmetic
Same fact pattern, two students: Mira's *"counted the loop, ignored the work
inside it"* across two assignments vs Arun's surface-similar loop claim that is
really a *different* difficulty. Live Jev runs on these fixtures: Mira →
`recurring` at confidence 0.84; Arun → **`similar`, NOT recurring**, at
confidence 0.35 — the near-coin-flip number itself routing that verdict to
professor review. No `if str1 == str2` does concept-level matching degraded by
paraphrase; and the negative control proves it discriminates rather than
pattern-matching "loop + wrong = recurring".

### Case 5 — failure behaves itself
`jev_model=typesafe/jev-nonexistent-model-xyz` → HTTP 400 "model does not
exist" → a **visible `jev_fallback` trail row** carrying the exact error, then
the chat checker answered and the report completed. A layer that fails
visibly degrades to layered defence; it never silently vanishes.

---

## Where code is genuinely better — said plainly

Hexraei measured it and moved it (`fa49e9e`, `ef54d9c`): models asked to do
**exact comparison on numbers** — "does the headline say 15/20 when the count
is 15/20?" — invent contradictions 4 times out of 5, and even reject *true*
sentences by citing the numbers that prove them. So counting, exact
score-matching, citation-existence and clean-sweep keywords live in code. That
is correct and it stays. Jev is not the replacement for that half; it is the
layer for what no regex enumerates: proportion, paraphrase, calibration.

## The judge-facing one-liner

> "Code catches the lies we predicted. Jev catches the lies we didn't predict
> — and tells us when it's not sure, so a person decides instead of a coin flip."

## Known limits (pre-empt the questions)

- The floor currently fires on `recurring` labels and report checks; 0.60 is a
  chosen threshold, not a law.
- Jev adds latency and cost per check; the deterministic layer keeps the
  common cases cheap.
- **Open item:** this branch predates main's mechanical checker rewrite
  (`check_claim_strength`); after the merge the two layers compose, and the
  post-merge regression pass (`./test.sh` clean shell + the 3 live cases in
  `SMOKE_RESULTS.md`) must be green before the demo.
