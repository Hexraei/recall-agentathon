# The `jev-compare` branch — evaluated, not merged

Everything in this folder documents a real, evaluated second-judge integration
(`typesafe/jev-1.13`, a decisions-API model) built on a separate branch and
never merged into `main`'s judged path. Per explicit team decision, `main`'s
compare/report checks stay fully code-based; `TYPSAFE_JEV_MODEL` stays unset
in `.env`, so the Jev transport never engages (`app/jev_compare.py` and
`app/jev_report_check.py` exist in the tree and are exercised by
`tests/test_jev_integration.py`, but sit dormant behind that flag).

Moved here from the repo root on a cleanup pass — nothing was deleted, only
relocated, because this is real project history worth keeping, not clutter.

- **`JEV_CONTEXT.md`** — the branch's own context doc: what was built, how it
  iterated, how to run it, what stayed open.
- **`CODE_AUDIT.md`** — a hostile five-lens review of the branch's code.
- **`CONTEXT.md`** — the case for why a model-based judgement layer might beat
  pure code checks, with real test cases.
- **`SMOKE_RESULTS.md`** — full smoke-test output and a judge recreation guide,
  as run on the branch.

See also [`../evidence/jev-eval-01-calibration.md`](../evidence/jev-eval-01-calibration.md)
for the specific confidence-calibration bug found and fixed in Jev's scoring
during evaluation.
