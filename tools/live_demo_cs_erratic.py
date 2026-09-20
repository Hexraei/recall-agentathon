"""Re-run the erratic CS identity live, with a fresh identity and fresh runs,
for the moment in the demo where a judge should watch the agent decide in
real time rather than read a result that was already computed.

Why this exists rather than just re-running tools/run_memory_demo.py
----------------------------------------------------------------------
memory.db's mem_cs_erratic_dept sittings are already advanced to COMPLETE /
NEEDS_REVIEW. Calling advance() on a run that has already finished does not
repeat the model call - it reads back what is already stored. Re-running the
existing tool against the existing group would LOOK like a live demo and
actually replay one, which is worse than not doing it at all if a judge asks
"is this calling the model right now."

This script builds a SEPARATE, brand-new identity (`mem_cs_erratic_live`) from
the same six real students' same real answers, with fresh run_ids, into its
own throwaway database - `memory-live.db`, never `memory.db`. Advancing those
runs is a genuine, first-time model call. The existing verified result in
memory.db (used for the robotics side of the demo, and as the recorded
evidence in docs/memory-demo-department-selection.md) is completely untouched
by running this any number of times.

Pre-seed vs. live (--live-from)
--------------------------------
A full 6-sitting run takes 2-3 minutes on stage, mostly because later
sittings have more history to read and sometimes trigger a revision loop
(the checker rejects a draft finding and sends it back for another model
call). That is real work, not padding, but nobody wants to stand there
watching sitting 1 - which has no history yet and always resolves in
seconds anyway.

--live-from N (default 4) advances sittings 1..N-1 QUIETLY first, with no
per-step trace printed, exactly the same real model calls, just not narrated.
Those are the "pre-seed" sittings - genuinely run, genuinely real, just done
before you started talking. Sittings N..last are then advanced WITH the full
verbose trace, printed as they happen - that is the "live" part a judge
watches happen in real time.

This is not faking anything: every sitting, pre-seeded or live, calls the
real model through the real app/flow.py pipeline. The only difference is
whether the trace is shown while it happens or beforehand. Pre-seeding is
required anyway, because a later sitting's comparison step can only see
history that an earlier sitting already wrote - sitting 4 cannot be
meaningfully "live" unless 1-3 already ran.

Run it on stage:

    .venv/bin/python tools/live_demo_cs_erratic.py                # live from sitting 4 (default)
    .venv/bin/python tools/live_demo_cs_erratic.py --live-from 5   # narrate only the last 2

Each sitting's REAL model call happens as you watch, printed as it happens -
same real answers, same real students, same shipping app/flow.py pipeline
that mem_cs_erratic_dept ran through when it was built. If you re-run this
script again later, it builds a fresh identity again (memory-live.db is
overwritten each time) - so it can be re-run for a second judge without the
answers changing, but the model call is genuinely new every time.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slice.config import load_env, settings as load_settings  # noqa: E402
from slice.llm import complete  # noqa: E402
from slice.store import Store  # noqa: E402

from tools.build_memory_demo import GROUPS, build  # noqa: E402
from tools.run_memory_demo import run_group, run_sitting  # noqa: E402

import sqlite3  # noqa: E402
import shutil  # noqa: E402

SOURCE_DB = ROOT / "webapp.db"
LIVE_DB = ROOT / "memory-live.db"

# The same six real students as mem_cs_erratic_dept, under a new identity id
# so this run's fresh run_ids never collide with the already-verified ones in
# memory.db. Everything else - department, category, why, members - is
# copied verbatim from the group this reruns; only id/display/expect differ,
# so the printed "why" text still explains the real selection rationale.
_BASE = next(g for g in GROUPS if g["id"] == "mem_cs_erratic_dept")
LIVE_GROUP = {
    **_BASE,
    "id": "mem_cs_erratic_live",
    "display": "Aravind S. (live rerun)",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--live-from", type=int, default=4,
        help=("1-based sitting number to start narrating live. Sittings "
              "before this run for real but quietly (pre-seed); this "
              "sitting onward is traced step by step as it happens (live). "
              "Default 4 - the first sitting with enough history for the "
              "model to reason over, and where revision loops start showing "
              "up. Pass 1 to narrate the whole chain."))
    args = ap.parse_args()

    for suffix in ("", "-wal", "-shm"):
        p = LIVE_DB.with_name(LIVE_DB.name + suffix)
        if p.exists():
            p.unlink()

    src_ro = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
    src_ro.row_factory = sqlite3.Row
    shutil.copy(SOURCE_DB, LIVE_DB)
    print(f"Fresh identity built from real webapp.db data -> {LIVE_DB.name}\n")

    store = Store(LIVE_DB)
    # build() returns the manifest shape run_group() expects - a group dict
    # with "sittings" (run_ids, dates, scores) filled in and "members"
    # dropped. Passing LIVE_GROUP itself here instead of this return value
    # is the bug that broke the first run of this script: LIVE_GROUP has no
    # "sittings" key until build() adds it.
    manifest = build(src_ro, store, [LIVE_GROUP])
    group = manifest[0]
    store.db.commit()

    load_env(ROOT / ".env")
    settings = load_settings()
    notes = (ROOT / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

    def flow_for(trace):
        from app.flow import build_flow
        return build_flow(call=complete, notes=notes, trace=trace)

    cut = max(1, min(args.live_from, len(group["sittings"])))
    pre_seed, live = group["sittings"][:cut - 1], group["sittings"][cut - 1:]

    if pre_seed:
        print(f"Pre-seeding sittings 1-{cut - 1} quietly - same real model "
              f"calls, just not narrated (sitting {cut} onward needs their "
              "history to exist first, the same way it would have if this "
              "demo group had really been sat over several weeks).\n")
        for s in pre_seed:
            run_sitting(store, settings, group, s, notes, flow_for, verbose=False)
            store.db.commit()
        print(f"\nPre-seed done. Now going live from sitting {cut}.\n")

    print("Advancing the remaining sitting(s) through the real pipeline, "
          "traced live - this is a real model call happening now, not a "
          "replay.\n")
    sittings_done = list(pre_seed)
    for s in live:
        sittings_done.append(
            run_sitting(store, settings, group, s, notes, flow_for, verbose=True))
        store.db.commit()

    print(f"\nFinal label this run: {sittings_done[-1]['label']}")
    print("(Re-run this script again for a fresh live call with the same "
          "real students - the answers are fixed, the model call is not.)")


if __name__ == "__main__":
    main()
