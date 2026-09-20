# CODE_AUDIT.md — hostile review of `jev-compare` (HEAD `c7f8762`)

Reviewed by five independent lenses (architecture, correctness, security,
testing, maintainability), then synthesized. Nothing was modified; the only
writes are this file and throwaway test runs. Verdict sections at the bottom.

Scope reviewed: the branch delta vs `origin/main` (13 commits behind main, by
design per current instructions), the two Jev integration modules
(`app/jev_compare.py`, `app/jev_report_check.py`), the report loop
(`app/report.py`), the compare handler and routing in `app/flow.py`,
`slice/config.py`, `scripts/load_key.sh`, the test suite, and the three
markdown deliverables (`CONTEXT.md`, `SMOKE_RESULTS.md`, `JEV_CONTEXT.md`).

---

## What the work does

Wires "Jev" (OpenRouter `api/alpha/decisions`, model `typesafe/jev-1.13`) in as
a *typed decisions* engine behind two seams, both behind the env flag
`TYPSAFE_JEV_MODEL` (empty = off, chat path untouched):

1. **Compare step** (`app/flow.py::handle_comparing`): Jev labels a student's
   difficulty `recurring/similar/improving/not_enough_evidence` with a
   confidence; below `jev_confidence_floor` (0.60) on a `recurring` verdict the
   run routes to professor review instead of confirming. Any Jev failure falls
   back to the chat model, recorded as a `failure` row.
2. **Report check** (`app/report.py::_run_check`): Jev answers two `noul`
   questions ("is this report false/unmeasurable/ad‑hominem anywhere?" and
   "which claim?"); low-confidence verdicts ship the report flagged
   `_unverified` rather than trusted or redrafted.

Confirmed by direct inspection and by running the suite: **86 tests pass**
(`./test.sh`, 25.6s, keyless).

---

## Findings, prioritized

### P1 — Correctness / honesty of the headline claim: "calibrated uncertainty" is a remap of one number

`app/jev_report_check.py:170-176`: for `noul` questions Jev returns **no
confidence field** ("noul answers carry no confidence field — the calibration
IS the probability" — own comment). When absent, code derives
`confidence = abs(noul - 0.5) * 2.0`.

- That derived "confidence" is a **deterministic transform of the same
  probability**, not an independent calibration channel. The `_unverified`
  routing decision (`body["_unverified"]`, `report.py:511-517`) is therefore
  decided entirely by where noul sits relative to 0.5 and 0.6 — i.e. by
  thresholds on one number wearing two names. The docstring's claim that
  "below the floor the verdict is not trusted *either way*" and CONTEXT.md's
  "channel of graded doubt that booleans don't have" oversell this: it is one
  scalar, remapped.
- Consequence already observed in `SMOKE_RESULTS.md` and admitted there as a
  caveat: **every clean, fact-conformant report observed (noul 0.55/0.10,
  0.43/0.14, 0.37/0.26) lands under the floor and always ships `_unverified`.**
  As configured, the faithful path is "accept only when flagged"; a decisive
  *clean accept* above the floor is empirically unreachable for honest output
  while a decisive reject (noul 0.99) is routine. That asymmetry means the
  routine happy path is essentially a rubber floor; CONTEXT.md case 3 presents
  the flagged shipping as a feature without stating it is the *only* observed
  happy path.

### P2 — `related_refs` is decoration, not the model's evidence

`jev_compare.py:233-244`: Jev's returned answer fields are ignored for
explanation/refs; the module substitutes the **criteria text itself** as
`explanation` (so "why" shown to professor/finding step is boilerplate, not the
model's reasoning) and computes `related_refs` as "all supported refs in the
entire prior history, sorted". A wide-coverage ref list is presented as the
*evidentiary basis* of this verdict whether or not Jev relied on it, and a
`not_enough_evidence` verdict ships the same populated refs (a caller can't
tell "none" from "everything"). This weakens exactly the "reading
comprehension, not pattern matching" claim the branch is meant to prove: the
proximate *why* is never transmitted by the Jev path.

### P3 — Broad exception laundering misclassifies bugs as outages

- `flow.py:290`: `except (ModelError, Exception)` — the first clause is dead
  (Exception subsumes ModelError) and the catch is broad enough to swallow
  genuine programming defects (`AttributeError`, `KeyError` raised *inside*
  the Jev path) and record them as `failure.kind == "jev_unavailable"`,
  silently falling back. A Jev Unavailable row must mean "Jev couldn't be
  reached/answered", not "our code has a typo". Narrow to `(JevError,
  network-ish)` or at minimum re-raise non-Jev errors.
- Consequence: `test_a_jev_outage_falls_back_visibly_and_the_run_survives`
  asserts proportionality between outages and chat-compares, but cannot
  distinguish a *real* Jev outage from an internal defect — the test passes
  identically under a code bug.

### P4 — Correctness: floor routing on compare fires only for `recurring`

`flow.py:487-494` (`_route_after_compare`): the below-floor professor ask is
gated on `label == "recurring"`. A `similar` or `improving` verdict at
confidence 0.05 sails through to draft/confirm without a human — even though
`improving` also drives `confirmed_recurring`-class outcomes and the module
docstring (`jev_compare.py:10-12`) says the floor exists to route *consequential
verdicts*. Either the gate is intentional (then document why only `recurring`
is consequential) or it's a hole. No test pins the `improving`-below-floor
behavior — likely never considered.

### P5 — Dead/obfuscated code in shipped logic

`jev_compare.py:231-232`:
```python
raise JevVerdict if False else JevError(...)   # noqa: unreachable tie-off
```
A conditional `raise` on a constant `False`, annotated to silence the tooling,
in production error handling. It works, but it's noise that invites exactly the
skeptical reading a demo judge will have. Replace with a plain `raise
JevError(...)`. Related smaller smells at `jev_compare.py:138`
(`__import__("datetime")` inline in `compute_week_gap`) and
`jev_compare.py:211` (`import httpx` re-imported inside the function while a
module-level import already exists).

### P6 — Report-check Jev verdict drops the "which claim" answer

`jev_report_check.py:173-174, 182`: `bad_claim` is asked (a second network
question, paying tokens) but `bad_noul` only goes into `meta` and **never into
the returned verdict nor the rejection detail**. The module's own docstring
(`_questions`, lines 107-110) says the second question exists so "a rejection
can name WHICH claim was false, which is what the redrafting prompt needs" —
the redrafting prompt (`report.py:189-194`) receives only generic
`failed_check="claim_strength"` and a detail string that never mentions the
claim. The second question currently buys nothing visible; either surface it in
`JevVerdict.detail`/ReportCheck.detail or drop the call.

### P7 — Security hygiene, mostly fine, two notes

- Credentials: `Authorization: Bearer <OPENROUTER_API_KEY>` to the decisions
  endpoint is the documented pattern; no key material in repo
  (`.env` untracked, verified via `git check-ignore`; `scripts/load_key.sh`
  reads from `~/outside-repo` with `set -euo pipefail` and env-wins
  precedence). Tests use a deliberately wrong-shaped key. Good.
- **Prompt-injection surface (accepted risk, but state it):** student-free-text
  passages and professor notes are interpolated raw into the Jev state bundle
  (`jev_compare.py:84-97`, passage text inside quotes; `jev_report_check.py`
  evidence strings). A crafted note could steer the judge. Defense in depth
  exists (code-side verdict/downgrade gates, `verdict_for`,
  `enforce_verdicts`, `enforce_pattern` all still run), so blast radius is
  limited to labels/explanations — but neither doc names this threat openly.
- `consistency.py`/`bakeoff.py` exist in tree; `consistency.db` (166 KB sqlite)
  is **tracked in git** — a binary run-artifact in history. Remove from
  tracking (`git rm --cached`) before the demo push; also several multi-MB PDFs
  are tracked, bloating the branch.

### P8 — Testing: good unit coverage of the seams, but the two *modules themselves* are untested

`tests/test_jev_integration.py` (449 lines) is genuinely good engineering
(deterministic judge queue with documented repeat semantics; guarded fallback
double that refuses unauthorized chat calls; wiring restored in `finally`;
proportionality assertions tying each fallback to a recorded outage). All pass.

Gaps:

- **No tests touch `jev_compare.judge` HTTP handling or
  `jev_report_check.judge` transport logic** — the decision-code parsing, HTTP
  status handling, `budget.record_tokens` accounting, and the JEV_MISSING
  answer-shape handling are exercised only by manual live smoke (recorded in
  SMOKE_RESULTS.md, runs of 19-20 Sep; **not machine-verifiable, and not
  reproducible by the next person**). `httpx.post` is trivially mockable with
  `respx`/monkeypatch — absence here is a choice, and it leaves the
  `confidence or 0.0` coercion (`jev_compare.py:243`), the non-200 path
  (`:217-219`), and `jev_report_check.judge`'s malformed-JSON behavior
  entirely unpinned.
- `jev_compare.compute_week_gap` has zero unit tests despite being pure —
  cheapest possible test target, and the branch's headline feature claims
  dates "computed in Python" as a selling point.
- No test exercises the `jev_confidence_floor` set *above* 1.0 or below 0.0
  (config accepts unvalidated float; `skip float(g(...))` won't fail until
  runtime mixing).
- The `test.sh` gate is green but note it was run with `-e` (per output
  artifact) — passing counts are honest, verified independently here.

### P9 — Maintainability notes (small)

- `jev_report_check.JevVerdict` duplicates the name of the Pydantic
  `jev_compare.JevVerdict` in the same package with a totally different shape
  (plain class vs Pydantic). Confusing at import time; rename one
  (`JevCheckVerdict`).
- `failed_check` is hardcoded `"claim_strength"` in `jev_report_check.py:60`
  even when the reason was *unmeasurable* or *ad-hominem* (the check prompt's
  categories 2 and 3). The back-edge redraft message tells the writer "claimed
  a pattern the counts do not support" — wrong guidance for an ad-hominem
  rejection. Add the reason.
- `flow.py` phrase `timed("compare", ...)` etc. — fine, but `_route_after_compare`
  takes `ask` as a parameter while `_ask_professor` is in the same closure;
  passing it around is ceremony, not generality.
- `slice/config.py` has no bounds check on `jev_confidence_floor`.
- The comparison's Jev-explanation-as-criteria-text (`P2`) also means
  `consistency.py`-style audits of "which transport said what" compare
  *boilerplate*, not reasoning.
- Docs: CONTEXT.md and JEV_CONTEXT.md carry the "pre-`ef54d9c` checker state is
  still open" caveat honestly — repeated three times across files; it should be
  stated once with a TODO pointer. Everything else in the docs is numeric and
  reproducible from SMOKE_RESULTS.md's own procedure — spot-checked cases 1, 2,
  5 against SMOKE_RESULTS.md lines 51-56/76-78; numbers match verbatim.

---

## Cross-cutting verdict per lens

| Lens | Assessment |
|---|---|
| **Architecture** | Sound seam design: Jev behind the report-run flow's existing call-fallback pattern, code still owns arithmetic (`verdict_for`, `enforce_pattern`, `compute_week_gap`, citation gates). Typed-question/state-block split against the decisions API is the right shape. Routing checkpoints (persist-before-route in `_route_after_compare`) show real earlier bugs were found and fixed structurally. **The one architectural crack** is the dual meaning of `confidence` across the two endpoints (choice-question native confidence vs derived-from-noul), which makes `jev_confidence_floor` two different predicates under one name. |
| **Correctness** | Logic verified by inspection and by running tests. P2 (decorative refs) and P6 (unused `bad_claim`) are real logic gaps, not style. P4 is a genuine routing hole. P1 is an *interpretive* correctness defect: the artifact's central marketing claim ("graded calibration from Jev") is only half-true for the report path, and the branch's demo exits through the floor every time for clean reports. |
| **Security** | Key handling correct. No injection vectors beyond model-prompt injection, which is inherent to the design (LLM judge on student text) and mitigated by the code-side gates. Binary DB and PDFs in git is hygiene, not vuln. |
| **Testing** | 86/86 pass, suite is keyless and well-shaped. Biggest gap: the two Jev HTTP transports themselves are unexercised by any automated test, leaving parsing/HTTP fallback to *recall* of manual smoke runs rather than pinned assertions. |
| **Maintainability** | Comments here are the best I've read in an agentathon: every design decision carries its measured reason. Docked for the `raise ... if False` line, the name collision, and the hardcoded `claim_strength`. |

---

## Final verdict

**Solid, demo-ready, doc-honest-in-the-aggregates — with two claims that need
softening and four fixes worth doing before the demo freeze.**

Not a green-light on the marketing language: P1 (derived confidence being
noul-in-disguise) and P2 (decorative `related_refs`) both mean CONTEXT.md
currently claims things the code does not fully deliver. The branch will
survive scrutiny as a *working pair of integrations*, and the state-machine
work (persist-then-route, visible fallbacks, code-side verdicts) is genuinely
good — but a sharp judge who reads `report.py:506-518` next to CONTEXT.md's
case 3 will find the "graded certainty channel" story only half-backed.

### Recommended next steps, in order

1. **Text fix (5 min, zero risk):** in CONTEXT.md case 3, replace "the *channel*
   of graded doubt that booleans don't have" with the honest version: "Jev's
   confidence for noul questions is code-derived (`|noul-0.5|×2`); clean
   reports observed always land flagged `_unverified` — accepted but never
   *silently* trusted." Saying this *first*, before the judge does it for you,
   is stronger than the current framing.
2. **Surface `bad_claim`** in ReportCheck.detail on reject (P6) — makes case 2
   and the redraft loop actually show which claim lies.
3. **Plumb a real explanation/refs from Jev** where the API exposes it, or
   rename `related_refs` to `prior_supported_refs` and mark it "context, not
   verdict evidence" (P2).
4. **Narrow the fallback catch** at `flow.py:290` to `JevError`/network-ish
   types so code bugs stop laundering as "Jev unavailable" (P3).
5. **Decide `improving`/floor behavior** — either route below-floor
   `improving` too, or document why not (P4).
6. **Add transport tests**: monkeypatch `httpx.post` for both `judge` functions
   — HTTP non-200, malformed JSON, missing fields, `budget.record_tokens`
   accounting, and `compute_week_gap` unit cases (P8).
7. Replace the `raise ... if False` tie-off with a plain raise, and rename one
   `JevVerdict` (P5/P9).
8. `git rm --cached consistency.db` (and consider `git rm --cached` on the
   large PDFs) before the next push to keep the branch slim.
