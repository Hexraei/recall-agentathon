# JEV_CONTEXT.md — the `jev-compare` branch

**Branch:** `jev-compare` (from `main` after the teammate's Phase 1–4b + quiz/report
commits). This file is the branch's context doc: what was built here, how it
iterated, how to run it, and what is still open. Companion to `MAIN_CONTEXT.md`
(`jev-compare` adds chapters 0 to the story written there — it does not change
the spec of record, `Mavericks_04.pdf`).

---

## Why this branch exists — one paragraph

The whole project rests on one judgement: *is this difficulty the same one we
saw before?* Measured on 19 Sept, the chat path answered that question
differently on identical input across consecutive runs — `recurring`, `similar`
AND `improving` (`consistency.py` exists because of that anecdote). A prompt can
be made reluctant (Ø commit 8241d4d's compare rewrite), but it cannot report its
own certainty. So this branch adds a **second transport behind the same step
contract**: Jev, the TypeSafe decisions model (`typesafe/jev-1.13`, OpenRouter
`/api/alpha/decisions` route). It answers a typed question with a probability
distribution and a confidence number — and the confidence number is a thing
CODE can act on, which is the whole point: "refuses to overstate" becomes
structural (a below-floor verdict routes to a human), not an instruction buried
in a prompt the model may ignore.

## The one rule everything here obeys

**Jev judges; code decides.** The model never touches control flow. Dates are
computed in Python (`compute_week_gap`) because Jev 1.13 reads dates as text and
cannot count — documented failure modes, not judgements worth asking of a
model. The compare prompt's decision rules are loaded verbatim as Jev's
criteria descriptions, so both transports judge by the same rubric and
`consistency.py` measures the transport, not the wording.

---

## What is done (commit order)

### ec133ff — Jev as the compare step's judge

- `app/jev_compare.py`: builds a typed state (objectives, current evidence,
  compacted prior records, week gap as a NUMBER), asks one `choice` question
  (labels: `recurring` / `similar` / `improving` / `not_enough_evidence`),
  returns a `JevVerdict` carrying `confidence` + `probabilities`.
- `app/flow.py handle_comparing`: when `TYPSAFE_JEV_MODEL` is set, Jev first;
  a `recurring` verdict with confidence below `JEV_CONFIDENCE_FLOOR` (default
  0.60) routes to professor review instead of trusting a coin flip; ANY Jev
  failure (HTTP, quota, shape, network) falls back to the chat transport
  *visibly* — a `jev_unavailable` failure record, never silence. Jev unset =
  behaviour byte-for-byte unchanged.
- `slice/config.py`: two new settings, both defaulted off/0.60.
- `scripts/load_key.sh`: bring the `~/.openrouter` key into the environment
  without it entering the repo.

Live-verified on the Mira story: first encounter → `not_enough_evidence` with
no Jev call at all; second encounter → `recurring` at confidence 0.84
(probabilities: recurring 0.88). Arun's negative control → `similar`, NOT
recurring, at confidence 0.35 — the calibration number doing exactly the job
that motivated the integration.

### d27d1ed — Jev as the report checker's second engine

- `app/jev_report_check.py`: two typed `noul` questions against a
  numbered-claims-vs-SQL-counts state — "is any claim false, unmeasurable, or
  about the person?" and "which claim?". `noul` carries **no confidence field**
  (verified live against the API), so confidence is derived as
  `|2*(noul−0.5)|` — the distance from a coin flip.
- `app/report.py _run_check()`: Jev first when set, chat checker as visible
  fallback (a `jev_fallback` trail row on any Jev error). Jev unset, or
  `settings=None` (the offline-test path), leaves the chat checker untouched
  and leaves no fallback debris. Below the confidence floor the report ships
  flagged `_unverified` rather than being trusted or endlessly redrafted on the
  same coin toss — identical calibration rule to compare.

Live-verified on the simulated cohort: a real report through the
draft→correct→check loop with noul=0.67/conf=0.34 shipped unverified (and said
so); a deliberately false report ("all questions right" where counts show 0/5)
got noul=0.99/conf=0.98 → rejected; a clean report landed at
noul=0.55/conf=0.10 → below-floor handling. Merged the teammate's 6 commits;
76/76 tests green at that point.

### d27d1ed..HEAD (uncommitted) — the floor-route fix

The bug: the floor routed to professor review from *inside* the try block,
**before the `comparison` row existed in the store**. The ask itself —
`_ask_professor` reading `ctx.latest("comparison")` — hit a `TypeError`
('NoneType' object is not subscriptable), which was swallowed by the same
`except` that discards Jev outages. A routing failure masqueraded as an outage;
the run fell back to chat and silently re-ran compare.

The fix (`app/flow.py`): `handle_comparing` now persists the `comparison` record
first, *then* one helper (`_route_after_compare`) does the routing in a fixed
order — (1) append the `jev_verdict` calibration row, (2) the comparison is
already stored, (3) only then ask the professor if label is `recurring` and
confidence is below the floor. `_ask_professor` tolerates a missing finding
(the floor routes before drafting; the checker's routes always have one). The
sent-back verdict's numbers now exist in the store even when the verdict was
sent back — "we judged it 0.35" is a record, not only the professor's question
text.

`tests/test_jev_integration.py` pins the contract with no network: calibration
recorded before the verdict's outcome is trusted; below-floor `recurring` asks
the professor and drafts nothing; high confidence confirms without a human;
outage falls back visibly (every chat compare traces to a recorded outage);
jev unset makes zero judge calls; report-check verifications for fallback,
clean-pass calibration, rejection, below-floor `_unverified`, and the
settings=None offline path.

**Suite: 86 passed, 0 failed** (`./test.sh`).

---

## The iterations, compressed

1. **Transport wired** (ec133ff): typed choice question, confidence floor as
   routing rule, visible fallback. Live-tested on Mira/Arun fixtures.
2. **Second engine behind the report check** (d27d1ed): same pattern, different
   contract — noul questions, derived confidence, `_unverified` flag instead of
   redraft-on-coinflip.
3. **The floor-route crash** (found by the failing integration tests): an ask
   raised inside the outage catch, so the fallback machinery consumed its own
   routing bug. Root-caused to ordering (append before persist), fixed by
   persist-before-route, tests rewritten to assert proportionality
   (outage-records == chat-fallback-count) instead of a one-off count.
4. **Teammate merges**: the quiz/root-cause wave (a1e8091 the onsubmit
   disable bug), question-bank rewrite, DB separation (webapp.db real vs
   demo.db simulated) — merged at 074d32c, all pre-existing behaviour kept.

## How to run it

```bash
source scripts/load_key.sh        # OpenRouter key from ~/.openrouter, not in repo
export TYPSAFE_JEV_MODEL=typesafe/jev-1.13          # default OFF
export JEV_CONFIDENCE_FLOOR=0.60                    # default 0.60
./test.sh                        # full keyless suite; 86 green expected
.venv/bin/python demo.py         # stubbed, no key — same flow, no Jev
.venv/bin/python live.py --full  # real model; Jev engages on encounter 2
```

Jev's endpoint refuses `/chat/completions`, so the transport cannot be
accidentally misrouted — the API enforces the shape we need. Unlisted in
`/models`; queried directly against `/api/alpha/decisions` with the same Bearer
key as everything else. Key handling: out of the repo (rotated repeatedly —
re-read `~/.openrouter` per session), never pasted into chat/repo/databases.

## Open on this branch

- **Uncommitted**: the floor-route fix in `app/flow.py` + the new test file.
  Commit them; the branch is otherwise 8 commits ahead of origin.
- **Push blocked**: last push to `github.com/Hexraei/recall-agentathon` got a
  403 — the authenticated identity (`404jaspernotfound`) has not been accepted
  as a collaborator. Root cause is external; until it clears, local commits are
  the only copy of this branch. Equivalent work is documented in
  `JEV_CONTEXT.md` while the push is pending.
- **`MAIN_CONTEXT.md` does not know about Jev yet** — it predates this branch.
  Fold a short note into its §0/§14 after the commit lands, or point readers of
  this file at it as the branch source of truth.
- **Consistency measurement of the transports** (`consistency.py` against both
  compare engines on identical input) is designed but unrun on this branch; the
  chat-path measurement from 19 Sept was the anecdote, the Jev-path version is
  the claim a judge will want to see.
