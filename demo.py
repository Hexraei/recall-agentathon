"""Phase 1: the whole story, with no model involved.

    python demo.py            all three encounters
    python demo.py --replay   plus the full record history for each run

What this proves, before a single token is spent:

  * the state machine turns, through all nine states
  * the back-edge fires - an overstated finding is rejected and re-drafted
  * the run suspends on the professor and resumes after an answer
  * the second encounter differs BECAUSE it read the first one's records
  * a superficially similar mistake is NOT flagged as recurring
"""
from __future__ import annotations

import sys
from pathlib import Path

from slice import callback
from slice.config import Settings, settings as load_settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import fixtures
from app.flow import build_flow
from app.stub import make_stub

DB = Path(__file__).parent / "run.db"
NOTES = (Path(__file__).parent / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
GREEN, RED, YELLOW = "\033[32m", "\033[31m", "\033[33m"


def banner(text: str) -> None:
    print(f"\n{BOLD}{'=' * 72}\n{text}\n{'=' * 72}{RESET}")


def submit(store: Store, settings: Settings, attempt: dict,
           answer: str | None = None) -> str:
    """Run one encounter end to end, answering the professor if asked."""
    run_id = store.create_run("recall", meta={"student_id": attempt["student_id"]})
    store.set_state(run_id, RunState.NEW_ATTEMPT)
    store.append(run_id, "attempt", attempt, produced_by="ingest")

    holder = [run_id]
    flow = build_flow(call=make_stub(store, holder), notes=NOTES)

    print(f"{DIM}  submit {attempt['student_id']}/{attempt['assignment_id']}{RESET}")
    state = advance(store, run_id, flow, settings)

    if state is RunState.NEEDS_REVIEW:
        pending = callback.pending(store, run_id)
        print(f"{YELLOW}  ⏸  suspended on the professor{RESET}")
        print(f"{DIM}     {pending[0].question.splitlines()[0]}{RESET}")
        if answer is None:
            print(f"{DIM}     (nobody answers - the run stays waiting){RESET}")
            return run_id
        print(f"{DIM}     professor answers: {answer!r}{RESET}")
        callback.answer(store, pending[0].id, answer, who="professor")
        store.set_state(run_id, RunState.RECORD_UPDATED)
        state = advance(store, run_id, flow, settings)

    report(store, run_id, state)
    return run_id


def report(store: Store, run_id: str, state: RunState) -> None:
    summary = store.latest(run_id, "summary")
    if summary is None:
        print(f"{RED}  ✗ ended in {state.value}{RESET}")
        failure = store.latest(run_id, "failure")
        if failure:
            print(f"{RED}    {failure['kind']}: {failure['detail']}{RESET}")
        return

    colour = GREEN if summary["comparison"] != "recurring" else YELLOW
    print(f"  comparison : {colour}{summary['comparison']}{RESET}")
    print(f"  status     : {summary['status']}")
    print(f"  finding    : {summary['statement']}")
    if summary["related"]:
        print(f"  supported by: {', '.join(summary['related'])}")
    print(f"  uncertain  : {summary['uncertainty']}")
    if summary["next_step"]:
        print(f"  next step  : {summary['next_step']}")

    verdict = summary["professor"]
    if verdict == "not_asked":
        print(f"{DIM}  professor   : not asked - the check accepted this finding{RESET}")
    elif verdict == "no_reply":
        print(f"{YELLOW}  professor   : asked, no reply yet - no next step issued{RESET}")
    else:
        print(f"  professor   : {GREEN}{verdict}{RESET}")

    drafts = len(store.history(run_id, "finding"))
    rejections = sum(1 for c in store.history(run_id, "check")
                     if c.payload["verdict"] == "rejected")
    if rejections:
        print(f"{DIM}  ({drafts} findings drafted, {rejections} rejected by the "
              f"checker and sent backwards){RESET}")


def replay(store: Store, run_id: str) -> None:
    print(f"\n{DIM}--- replay {run_id} ---{RESET}")
    for v in store.replay(run_id):
        payload = str(v.payload)
        print(f"{DIM}{v.seq:>3}  {v.kind:<12} {v.produced_by:<18} "
              f"{payload[:78]}{RESET}")


def main() -> None:
    if DB.exists():
        DB.unlink()
    store = Store(DB)
    settings = load_settings()
    runs = []

    banner("ENCOUNTER 1 — Mira, assignment 1, week 3\n"
           "No history exists. The system must not claim a pattern.")
    runs.append(submit(store, settings, fixtures.MIRA_1))

    banner("ENCOUNTER 2 — Mira, assignment 2, week 7\n"
           "Reads encounter 1. A pattern is possible; the first finding overstates it.")
    runs.append(submit(store, settings, fixtures.MIRA_2, answer="confirm"))

    banner("NEGATIVE CONTROL — Arun\n"
           "A different student, a superficially similar mistake, a different cause.")
    runs.append(submit(store, settings, fixtures.ARUN_1))
    runs.append(submit(store, settings, fixtures.ARUN_3))

    banner("DUPLICATE — Mira resubmits assignment 1\n"
           "A duplicate would fake a second encounter. Ingest must refuse it.")
    submit(store, settings, fixtures.MIRA_1)

    if "--replay" in sys.argv:
        for run_id in runs:
            replay(store, run_id)

    store.close()


if __name__ == "__main__":
    main()
