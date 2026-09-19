"""Fill the quiz database with simulated students, so the report agents have
something real to read before anyone walks in.

Each persona has a DESIGNED misconception - not random wrong answers. That is
what makes this a test rather than a demo: we know what the report should find,
so we can tell whether it found it or just wrote something plausible.

    .venv/bin/python simulate.py            # default cohort
    .venv/bin/python simulate.py --reset    # wipe first
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from slice.store import Store

from app import bank, roster

DB = Path(__file__).parent / "webapp.db"


PERSONAS = [
    # (name, department, blind_concepts, accuracy_elsewhere)
    # blind_concepts: always wrong here, and wrong on the SAME kind of
    # distractor, which is what a real misconception looks like.
    ("Divya R",    "computer_science", {"counting work inside loops"}, 0.9),
    ("Karthik S",  "computer_science", {"counting work inside loops"}, 0.8),
    ("Meena P",    "computer_science", {"counting work inside loops",
                                        "relating loop structure to growth rate"}, 0.85),
    ("Arjun N",    "computer_science", {"reasoning about references and copies"}, 0.9),
    ("Sneha T",    "computer_science", set(), 0.95),
    ("Vikram J",   "computer_science", {"identifying a terminating base case"}, 0.7),
    ("Priya K",    "robotics", {"reasoning about singularities and degeneracy"}, 0.85),
    ("Rahul M",    "robotics", {"reasoning about singularities and degeneracy"}, 0.8),
    ("Anita G",    "robotics", {"relating controller terms to observed error behaviour"}, 0.9),
    ("Suresh B",   "robotics", set(), 0.9),
]


def run(reset: bool = False) -> None:
    if reset and DB.exists():
        for p in DB.parent.glob("webapp.db*"):
            p.unlink()
        print("wiped webapp.db")

    store = Store(DB)
    roster.init(store)
    rng = random.Random(7)   # seeded: the same cohort every time, so a
                             # report that changes means the AGENT changed

    for i, (name, dept, blind, acc) in enumerate(PERSONAS, start=1):
        sid = roster.create_student(
            store, name, f"98{i:04d}{i:04d}"[:10], f"2024{dept[:2].upper()}{i:03d}", dept)
        for q in bank.for_department(dept):
            if q.concept in blind:
                # Wrong, and deliberately the FIRST wrong option - so the class
                # view shows students converging on one distractor, which is
                # what a real shared misconception produces.
                chosen = next(o.key for o in q.options if not o.correct)
            elif rng.random() < acc:
                chosen = q.answer_key
            else:
                chosen = rng.choice([o.key for o in q.options if not o.correct])
            roster.record(store, sid, q, chosen, seconds=rng.uniform(4, 25))
        got, asked = roster.score(store, sid)
        flag = ", ".join(sorted(blind)) or "no designed gap"
        print(f"  {name:<12} {dept:<17} {got:>2}/{asked}   [{flag}]")

    print("\nclass sizes:",
          {d: roster.class_size(store, d) for d in bank.DEPARTMENTS})
    return store


def warm(store) -> None:
    """Generate every report up front so the demo never waits on a model.

    Reports are cached in the `reports` table, so this is the difference
    between a teacher clicking a department and seeing it instantly, and a
    teacher watching a blank page for a minute while Groq queues. The
    "Re-run the agent" button on each page still does it live, which is what
    you press when someone asks to watch it happen.
    """
    import time as _t
    from slice.config import settings as load_settings
    from app import report

    settings = load_settings()
    for dept in bank.DEPARTMENTS:
        if roster.class_size(store, dept) == 0:
            continue
        t = _t.time()
        try:
            b = report.for_class(store, dept, settings, force=True)
            print(f"  class {dept:<17} {_t.time()-t:5.1f}s  {b['_revisions']} draft(s)")
        except Exception as e:
            print(f"  class {dept:<17} {_t.time()-t:5.1f}s  FAILED: "
                  f"{type(e).__name__}: {str(e)[:90]}")
        for stu in roster.students_in(store, dept):
            got, asked = roster.score(store, stu["id"])
            if asked == 0:
                continue
            t = _t.time()
            # One student's report failing must not cost the other nine theirs.
            # The page regenerates on demand anyway, so a miss here degrades to
            # "that one is slow the first time", not "the warm pass died".
            try:
                b = report.for_student(store, stu["id"], settings, force=True)
                print(f"  {stu['name']:<23} {_t.time()-t:5.1f}s  "
                      f"{b['_revisions']} draft(s)")
            except Exception as e:
                print(f"  {stu['name']:<23} {_t.time()-t:5.1f}s  FAILED: "
                      f"{type(e).__name__}: {str(e)[:90]}")


if __name__ == "__main__":
    st = run(reset="--reset" in sys.argv)
    if "--warm" in sys.argv:
        print("\ngenerating reports (this is the slow part, once):")
        warm(st)
