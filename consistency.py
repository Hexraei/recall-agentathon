"""Does the comparison step agree with itself?

    python consistency.py            10 trials of encounter 2
    python consistency.py --trials 5 --case arun

The whole project rests on one judgement: is this difficulty the same one we
saw before? If that answer changes between runs, nothing built on top of it
means anything, and a demo is a coin toss.

Observed by accident during a rate-limit test: the same encounter returned
`recurring`, then `similar`, then `improving` on three consecutive runs. This
script exists to turn that anecdote into a number.

Run it before touching the compare prompt, and again after, so "we improved it"
is a measurement rather than a feeling.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

from slice import retrieve
from slice.config import settings as load_settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import fixtures
from app.flow import build_flow
from slice.llm import complete

NOTES = (Path(__file__).parent / "corpus" / "ds-notes.md").read_text(encoding="utf-8")
DB = Path(__file__).parent / "consistency.db"

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m")

# What the right answer is, and why. A model is allowed to be uncertain; it is
# not allowed to be wrong in the opposite direction.
CASES = {
    "mira": {
        "history": [fixtures.MIRA_1],
        "probe": fixtures.MIRA_2,
        "want": "recurring",
        "acceptable": {"recurring", "similar"},
        "why": ("Same difficulty - counted the loop, ignored the work inside it - "
                "in two different tasks. `similar` is a defensible hedge. "
                "`improving` is wrong: she made the same mistake again."),
    },
    "arun": {
        "history": [fixtures.ARUN_1],
        "probe": fixtures.ARUN_3,
        "want": "similar",
        "acceptable": {"similar", "not_enough_evidence"},
        "why": ("Surface-similar to Mira's difficulty and to nothing in Arun's "
                "own history. `recurring` here is a false positive - the worst "
                "failure this system has."),
    },
}


def one_trial(settings, case: dict) -> str | None:
    """Fresh store every time, so no trial can see another's records."""
    if DB.exists():
        DB.unlink()
    store = Store(DB)
    try:
        retrieve.ingest(store, str(Path(__file__).parent / "corpus"))
    except Exception:
        pass
    flow = build_flow(call=complete, notes=NOTES)

    for attempt in case["history"] + [case["probe"]]:
        run_id = store.create_run("recall", meta={"student_id": attempt["student_id"]})
        store.set_state(run_id, RunState.NEW_ATTEMPT)
        store.append(run_id, "attempt", attempt, produced_by="ingest")
        advance(store, run_id, flow, settings)

    comparison = store.latest(run_id, "comparison")
    store.close()
    return comparison["label"] if comparison else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=10)
    p.add_argument("--case", default="mira", choices=sorted(CASES))
    args = p.parse_args()

    settings = load_settings()
    case = CASES[args.case]
    print(f"{BOLD}{args.case}: expecting {case['want']}{RESET}")
    print(f"{DIM}{case['why']}{RESET}")
    print(f"{DIM}{args.trials} trials, fresh store each time, "
          f"model {settings.model}{RESET}\n")

    labels = []
    for n in range(args.trials):
        label = one_trial(settings, case) or "FAILED"
        labels.append(label)
        mark = (f"{GREEN}✓{RESET}" if label == case["want"]
                else f"{YELLOW}~{RESET}" if label in case["acceptable"]
                else f"{RED}✗{RESET}")
        print(f"  {mark} trial {n + 1:>2}: {label}", flush=True)

    counts = collections.Counter(labels)
    exact = counts[case["want"]]
    ok = sum(counts[l] for l in case["acceptable"])
    print(f"\n{BOLD}distribution{RESET}")
    for label, n in counts.most_common():
        bar = "█" * n
        colour = (GREEN if label == case["want"]
                  else YELLOW if label in case["acceptable"] else RED)
        print(f"  {colour}{label:<22}{RESET} {bar} {n}/{args.trials}")

    print(f"\nexact  : {exact}/{args.trials}")
    print(f"defensible: {ok}/{args.trials}")
    if ok < args.trials:
        print(f"\n{RED}{args.trials - ok} trials gave an answer that is wrong, not "
              f"merely cautious.{RESET}")
        print(f"{DIM}The comparison prompt is the thing to fix. Re-run this "
              f"after changing it.{RESET}")
    elif exact < args.trials:
        print(f"\n{YELLOW}Every answer was defensible, but it is not stable. "
              f"A demo will show whichever one it feels like.{RESET}")
    else:
        print(f"\n{GREEN}Stable across {args.trials} trials.{RESET}")


if __name__ == "__main__":
    main()
