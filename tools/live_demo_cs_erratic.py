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

Run it on stage:

    .venv/bin/python tools/live_demo_cs_erratic.py

Each sitting's REAL model call happens as you watch, printed as it happens -
same real answers, same real students, same shipping app/flow.py pipeline
that mem_cs_erratic_dept ran through when it was built. If you re-run this
script again later, it builds a fresh identity again (memory-live.db is
overwritten each time) - so it can be re-run for a second judge without the
answers changing, but the model call is genuinely new every time.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slice.config import load_env, settings as load_settings  # noqa: E402
from slice.llm import complete  # noqa: E402
from slice.store import Store  # noqa: E402

from tools.build_memory_demo import GROUPS, build  # noqa: E402
from tools.run_memory_demo import run_group  # noqa: E402

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
    live_manifest_group = manifest[0]
    store.db.commit()

    load_env(ROOT / ".env")
    settings = load_settings()
    notes = (ROOT / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

    print("Advancing each sitting through the real pipeline - this is a live "
          "model call, not a replay.\n")
    result = run_group(store, settings, live_manifest_group, notes, verbose=True)
    store.db.commit()

    print(f"\nFinal label this run: {result['sittings'][-1]['label']}")
    print("(Re-run this script again for a fresh live call with the same "
          "real students - the answers are fixed, the model call is not.)")


if __name__ == "__main__":
    main()
