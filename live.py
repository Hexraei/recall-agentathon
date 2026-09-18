"""One real model call, end to end, so you can see the pipe connect.

    python live.py               extraction on Mira's first submission
    python live.py --step compare
    python live.py --full        the whole two-encounter story, real model

This is separate from demo.py deliberately. demo.py proves the architecture with
no key and no network - it is what you fall back to when the venue wifi dies.
This proves the model path. Keep both.

What to watch, and it is not the prose: whether the model returns something that
VALIDATES against the schema, and whether the passages it quotes survive the
citation check. Fluent output that fails both is the normal first result.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from slice.budget import Budget
from slice.config import settings as load_settings
from slice.llm import complete
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import fixtures, provenance
from app.flow import (build_compare_messages, build_extract_messages, build_flow)
from app.schema import Comparison, EvidenceSet

DB = Path(__file__).parent / "live.db"
NOTES = (Path(__file__).parent / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
GREEN, RED, YELLOW, CYAN = "\033[32m", "\033[31m", "\033[33m", "\033[36m"


def preflight(settings) -> bool:
    if not settings.api_key:
        print(f"{RED}No OPENROUTER_API_KEY.{RESET}")
        print(f"{DIM}  cp .env.example .env, then paste the key after "
              f"OPENROUTER_API_KEY={RESET}")
        return False
    print(f"{DIM}model    : {settings.model}{RESET}")
    print(f"{DIM}fallback : {settings.fallback_model}{RESET}")
    print(f"{DIM}ceiling  : {settings.max_tokens} tokens/request, "
          f"{settings.max_tokens_per_run} per run{RESET}\n")
    return True


def one_call(step: str) -> None:
    """Make a single real call and show what came back, and whether it holds."""
    settings = load_settings()
    if not preflight(settings):
        sys.exit(1)

    if DB.exists():
        DB.unlink()
    store = Store(DB)
    run_id = store.create_run("recall", meta={"student_id": "mira"})
    store.append(run_id, "attempt", fixtures.MIRA_1, produced_by="ingest")
    budget = Budget(store, run_id, settings)

    attempt = fixtures.MIRA_1
    if step == "extract":
        messages, schema = build_extract_messages(attempt, NOTES), EvidenceSet
    elif step == "compare":
        messages = build_compare_messages(
            {"items": [], "uncertainty_notes": []}, {"evidence": [], "finding": [],
                                                     "review": []},
            attempt["learning_objectives"])
        schema = Comparison
    else:
        print(f"{RED}unknown step {step!r}{RESET}")
        sys.exit(1)

    print(f"{BOLD}step: {step}{RESET}")
    print(f"{DIM}submission: {attempt['submission'][:70]}...{RESET}\n")

    started = time.time()
    try:
        result = complete(settings=settings, budget=budget, messages=messages,
                          schema=schema, step=step)
    except Exception as e:
        print(f"{RED}✗ {type(e).__name__}: {e}{RESET}")
        print(f"{DIM}  This is the kit classifying the failure rather than "
              f"raising a raw HTTP error. 402 means the key; 429 means the "
              f"provider.{RESET}")
        store.close()
        sys.exit(1)
    elapsed = time.time() - started

    print(f"{GREEN}✓ returned a valid {schema.__name__} in {elapsed:.1f}s{RESET}")
    print(f"{DIM}  tokens spent this run: "
          f"{int(store.counter(run_id, 'tokens'))}{RESET}\n")
    print(json.dumps(result.model_dump(), indent=2)[:1400])

    # The part that matters more than the prose.
    if isinstance(result, EvidenceSet):
        sources = {f"{attempt['assignment_id']}#response": attempt["submission"],
                   "course_notes": NOTES}
        checked = provenance.check_evidence(result.items, sources)
        bad = provenance.unsupported(checked)
        print(f"\n{BOLD}citation check{RESET} {DIM}(code, no model){RESET}")
        for item in checked:
            mark = f"{GREEN}✓{RESET}" if item.supported else f"{RED}✗{RESET}"
            print(f"  {mark} {item.passage[:62]}")
            if not item.supported:
                print(f"    {RED}{item.note}{RESET}")
        if bad:
            print(f"\n{YELLOW}{len(bad)} of {len(checked)} rows could not be "
                  f"established. They are KEPT and marked, never dropped.{RESET}")
            print(f"{DIM}Usually the model paraphrased instead of quoting. That is "
                  f"a prompt problem, and the check is what makes it visible.{RESET}")
        else:
            print(f"\n{GREEN}every passage appears verbatim in its source{RESET}")

    store.close()


def full_story() -> None:
    """Both encounters, real model, so the second one's difference is real."""
    settings = load_settings()
    if not preflight(settings):
        sys.exit(1)

    if DB.exists():
        DB.unlink()
    store = Store(DB)

    def trace(step: str, secs: float, detail: str) -> None:
        # A silent terminal during a 20-second call looks hung, and a run that
        # looks hung is one the audience stops believing in.
        print(f"  {GREEN}✓{RESET} {step:<9} {DIM}{secs:5.1f}s{RESET}  {detail}",
              flush=True)

    flow = build_flow(call=complete, notes=NOTES, trace=trace)

    for label, attempt in (("ENCOUNTER 1 — no history", fixtures.MIRA_1),
                           ("ENCOUNTER 2 — reads encounter 1", fixtures.MIRA_2)):
        print(f"\n{BOLD}{'=' * 64}\n{label}\n{'=' * 64}{RESET}")
        run_id = store.create_run("recall", meta={"student_id": attempt["student_id"]})
        store.set_state(run_id, RunState.NEW_ATTEMPT)
        store.append(run_id, "attempt", attempt, produced_by="ingest")

        started = time.time()
        state = advance(store, run_id, flow, settings)
        print(f"{DIM}  {time.time() - started:.1f}s, "
              f"{int(store.counter(run_id, 'tokens'))} tokens, ended {state.value}{RESET}")

        comparison = store.latest(run_id, "comparison")
        finding = store.latest(run_id, "finding")
        if comparison:
            print(f"  comparison : {CYAN}{comparison['label']}{RESET}")
            print(f"  {DIM}{comparison['explanation'][:100]}{RESET}")
        if finding:
            print(f"  finding    : {finding['statement'][:100]}")
        rejections = [c.payload for c in store.history(run_id, "check")
                      if c.payload["verdict"] == "rejected"]
        for r in rejections:
            print(f"  {YELLOW}↩ rejected ({r['failed_check']}) and sent "
                  f"backwards{RESET}")
            print(f"    {DIM}{r['detail'][:90]}{RESET}")
        if state is RunState.NEEDS_REVIEW:
            print(f"  {YELLOW}⏸ suspended on the professor{RESET}")

    store.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--step", default="extract", choices=["extract", "compare"])
    p.add_argument("--full", action="store_true")
    args = p.parse_args()
    full_story() if args.full else one_call(args.step)
