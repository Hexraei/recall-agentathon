"""Run the real agent pipeline over the last sitting of each synthetic identity.

This is the check the demo rests on, so it runs the SHIPPING flow - app/flow.py
built by build_flow(), advanced by slice/runner.py - against the database
tools/build_memory_demo.py produced. Nothing about the comparison step is
special-cased for the demo.

What we are looking for:
  Category A -> label "recurring", citing evidence from earlier sittings.
  Category B -> anything BUT a confident "recurring". A correct run here names
                no pattern, or says it lacks the evidence, or hands off to a
                human. That outcome is the demo, not a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slice import callback  # noqa: E402
from slice.config import load_env, settings as load_settings  # noqa: E402
from slice.llm import complete  # noqa: E402
from slice.records import RunState  # noqa: E402
from slice.runner import advance  # noqa: E402
from slice.store import Store  # noqa: E402

from app import history  # noqa: E402
from app.flow import build_flow  # noqa: E402

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
GREEN, RED, YELLOW, CYAN = "\033[32m", "\033[31m", "\033[33m", "\033[36m"


def run_sitting(store: Store, settings, group: dict, sitting: dict, notes: str,
                flow_for, verbose: bool) -> dict:
    """Advance one sitting through the real flow and report what it concluded."""
    run_id = sitting["run_id"]

    # What this sitting can see of the identity's past. Read BEFORE advancing,
    # because that is the question the comparison step is about to ask.
    prior = history.prior_records(store, group["id"], run_id)
    earlier = {p.get("assignment_id") for p in prior["evidence"]}
    earlier.discard(None)

    print(f"\n{DIM} sitting {sitting['sitting']}  {sitting['date']}  "
          f"{sitting['score']}/20  (real answers from {sitting['real_student_name']}){RESET}")
    print(f"{DIM}   history visible: {len(prior['evidence'])} evidence rows "
          f"from {len(earlier)} earlier sitting(s){RESET}")

    def trace(step, secs, detail):
        if verbose:
            print(f"{DIM}   {step:<9} {secs:5.1f}s  {detail}{RESET}")

    state = advance(store, run_id, flow_for(trace), settings)

    asked = None
    if state is RunState.NEEDS_REVIEW:
        pending = callback.pending(store, run_id)
        asked = pending[0].question if pending else "(no question recorded)"
        print(f"{YELLOW}   paused for a human: {asked.splitlines()[0]}{RESET}")

    comparison = store.latest(run_id, "comparison") or {}
    finding = store.latest(run_id, "finding") or {}
    check = store.latest(run_id, "check") or {}
    label = comparison.get("label")

    print(f"   comparison : {CYAN}{label}{RESET}")
    if comparison.get("explanation"):
        print(f"   explanation: {comparison['explanation']}")
    refs = comparison.get("related_refs") or []
    print(f"   cites      : {', '.join(refs) or '(none)'}")
    if finding:
        print(f"   finding    : {finding.get('status')} - {finding.get('statement', '')}")

    return {
        "sitting": sitting["sitting"], "date": sitting["date"],
        "run_id": run_id, "score": sitting["score"],
        "real_student_id": sitting["real_student_id"],
        "real_student_name": sitting["real_student_name"],
        "prior_evidence_rows": len(prior["evidence"]),
        "prior_assignments": sorted(earlier),
        "label": label,
        "explanation": comparison.get("explanation"),
        "related_refs": refs,
        "finding": finding or None, "check": check or None,
        "state": state.value, "paused_for_human": asked,
    }


def run_group(store: Store, settings, group: dict, notes: str,
              verbose: bool) -> dict:
    """Replay every sitting for one identity, oldest first.

    Order matters and is the reason this is not just a call on the last run.
    app/history.py builds a student's record out of the `evidence` rows earlier
    runs WROTE - and a run only writes them when it is advanced. Advance only
    the final sitting and its history is legitimately empty, so even a real
    recurrence is reported as not_enough_evidence. Each sitting has to actually
    happen before the next one can remember it.
    """
    print(f"\n{BOLD}{'=' * 72}\n[Category {group['category']}] {group['display']} "
          f"({group['id']}) - {group['department']}\n{'=' * 72}{RESET}")
    print(f"{DIM}{group['why']}{RESET}")
    print(f"{DIM}expecting on the final sitting: {group['expect']}{RESET}")

    def flow_for(trace):
        return build_flow(call=complete, notes=notes, trace=trace)

    sittings = [run_sitting(store, settings, group, s, notes, flow_for, verbose)
                for s in group["sittings"]]
    final = sittings[-1]

    # Scored across every sitting that HAD a history to read, not just the last
    # one. Reading only the final sitting throws away most of the evidence and
    # turns ordinary model variance into a pass or a fail: on mem_cs_a the
    # recurrence is found on sittings 2 and 3 and missed on 4, and "missed it
    # once in three" is a more honest thing to report than either "it works" or
    # "it failed".
    scored = [s for s in sittings if s["prior_evidence_rows"] > 0]
    hits = [s for s in scored if s["label"] == "recurring"]

    if group["category"] == "A":
        ok = len(hits) > 0
        detail = (f"found the recurrence on {len(hits)} of {len(scored)} "
                  "sittings that had a history to read")
    elif group.get("clean_control"):
        # Nothing to find, so any recurrence claim is an invention.
        ok = not hits
        detail = (f"claimed no recurrence on all {len(scored)} sittings"
                  if ok else
                  f"claimed a recurrence on {len(hits)} of {len(scored)} "
                  "sittings, with nothing there to find")
    else:
        # A near-miss group shares a concept, so `recurring` is defensible -
        # what matters is that any such claim is cited and sent to a human.
        unreviewed = [s for s in hits if s["state"] != "needs_review"]
        ok = not unreviewed
        detail = (f"{len(hits)} of {len(scored)} sittings claimed a recurrence; "
                  + ("every one cited its evidence and paused for a human"
                     if not unreviewed else
                     f"{len(unreviewed)} closed WITHOUT human review"))

    mark = f"{GREEN}as expected{RESET}" if ok else f"{RED}NOT as expected{RESET}"
    print(f"\n   {BOLD}final sitting: {final['label']}{RESET}")
    print(f"   {detail} ({mark})")

    return {**{k: v for k, v in group.items() if k != "sittings"},
            "sittings": sittings, "final_label": final["label"],
            "final_run_id": final["run_id"],
            "sittings_with_history": len(scored),
            "recurring_claims": len(hits),
            "outcome": detail,
            "meets_expectation": ok}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "memory.db"))
    ap.add_argument("--manifest", default=str(ROOT / "docs" / "memory-demo-manifest.json"))
    ap.add_argument("--only", help="run one group id")
    ap.add_argument("--quiet", action="store_true",
                    help="hide per-step timings")
    args = ap.parse_args()

    load_env(ROOT / ".env")
    settings = load_settings()
    notes = (ROOT / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if args.only:
        manifest = [g for g in manifest if g["id"] == args.only]

    store = Store(args.db)
    results = [run_group(store, settings, g, notes, not args.quiet)
               for g in manifest]
    store.db.commit()

    out = ROOT / "docs" / "memory-demo-results.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print(f"\n{BOLD}{'=' * 72}\nSUMMARY\n{'=' * 72}{RESET}")
    for r in results:
        mark = f"{GREEN}ok{RESET}" if r["meets_expectation"] else f"{RED}CHECK{RESET}"
        trail = " -> ".join(str(s["label"]) for s in r["sittings"])
        print(f"  [{r['category']}] {r['display']:<12} {mark}")
        print(f"{DIM}      {trail}{RESET}")
        print(f"{DIM}      {r['outcome']}{RESET}")
    print(f"\nresults -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
