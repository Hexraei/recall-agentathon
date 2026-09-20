"""The one-button, plain-English version of the persistent-memory demo.

Everything else in this project's memory demo (6 identities, categories A/B,
department-level statistics, 7-sitting chains) is real and correct, but it is
built for someone reading the docs, not a judge watching for thirty seconds.
This module is the opposite: 2, 3, or 4 real students, in one of two real
departments, one button per combination, one real model call per new
sitting, one plain verdict - and, if the system pauses, a real
Confirm/Reject a teacher can act on, not just a sentence saying it happened.

Two departments, two genuinely different real stories
-------------------------------------------------------
**Robotics - the clean pattern.** Nearly the whole real cohort shares one
exact misconception: they assume a robot's forward calculation just reverses
to find where it started, which it does not. A chain of robotics students who
all made exactly this mistake reliably converges on "recurring" - the system
confidently catching a real, repeated, shared error.

**Computer science - the honest, erratic case.** No single misconception
dominates this department - three different concepts are tied at 10 of 14
students each (see docs/memory-demo-department-selection.md for the measured
counts). A chain built from CS students picked for genuinely different
concept profiles produces real variety instead - "similar", "improving",
"not enough evidence" - and the system does not force a "recurring" verdict
just because it was asked to look for one. This is the same real members, in
the same order, as the already-verified mem_cs_erratic_dept identity.

Showing both, one after the other, is a stronger claim than either alone: it
is not that the system always says "recurring" - it says so exactly when the
real data supports it, and stays honestly uncertain when it does not.

In both cases: the first sitting has nothing to compare against. Each
sitting after that is where the system's memory does its one job - it reads
everyone before it and decides, for real, whether this looks like the same
thing happening again. Longer chains (3, 4) are a stronger version of
whichever claim the department is making, at the cost of one more live model
call each.

This is a real model call, not a replay
----------------------------------------
Every click on "Run it live" builds a brand-new chain of runs in a throwaway
database (recall-live-demo.db, wiped and rebuilt each time) from the same
real students' same real answers, then advances them through the exact same
shipping pipeline (app/flow.py) the rest of this project uses. Every sitting
but the last is advanced immediately, quietly, because a later sitting
cannot have anything to remember unless the earlier ones already happened -
the same reasoning tools/live_demo_cs_erratic.py documents at length. Only
the LAST sitting is the one the button times: that is the real, first-time
model call a judge watches happen.

Never touches memory.db or webapp.db - both stay exactly as they are no
matter how many times this runs.

Chains are chosen, not just taken in cohort order
--------------------------------------------------
Robotics candidates all share the exact same wrong option (B) on the exact
same question (rb_t1_q2), for the exact same stated misconception - that is
the one true signal this half of the demo exists to show. Beyond that, each
student has 3-5 OTHER wrong answers of their own, and with only 7 students in
the whole robotics cohort sharing rb_t1_q2#B, some incidental overlap on
those other questions is close to unavoidable once a chain gets past 2
students. Rather than pretend that away, each chain length was picked by
checking every possible combination directly against webapp.db and keeping
the one with the least incidental overlap:

    2: Harshavaradhan G, Krish               - zero incidental overlap
    3: Sathya Sa, JYOTHISH, Krish            - one incidental overlap
                                                (Sathya Sa & JYOTHISH also
                                                both miss rb_t4_q3, for
                                                different, unrelated reasons)
    4: Sathya Sa, JYOTHISH, N.karthikeyn, Krish - three incidental overlaps,
                                                one per adjacent pair, none
                                                touching the target question

A thorough comparison step sometimes notices an incidental overlap and
mentions it (see git history: the first-ever run of this file, with a
noisier pair, correctly said "similar" instead of "recurring" because of
exactly this) - that is honest model behaviour, not a bug, but it muddies a
demo meant to be readable in one glance. These specific chains were checked
live and reliably return "recurring" on the final sitting; if you swap the
membership, re-verify before relying on it on stage.

Computer science chains are simply the first N, N+1, ... members of
mem_cs_erratic_dept in that order - already checked in
docs/memory-demo-department-selection.md to produce genuine label variety,
not picked or re-verified separately for this module.
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

from slice import callback
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import bank
from app.flow import build_flow
from tools.build_memory_demo import attempt_for, read_sitting

# Same three-weeks-apart convention as the rest of the memory demo
# (tools/build_memory_demo.py), so a chain's dates read like real sittings of
# a term rather than quizzes taken minutes apart.
FIRST_SITTING = date(2026, 6, 8)
WEEKS_BETWEEN = 3

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DB = ROOT / "webapp.db"
LIVE_DB_DIR = ROOT / "recall-live-demo"
"""Each run gets its own database file, LIVE_DB_DIR/<run_id>.db, rather than
one shared file wiped on every click. A single shared file meant confirming
or rejecting an earlier run's pending review after starting a second run
destroyed the first run's data before the teacher could act on it - found
live, running robotics then computer science in the same demo session before
confirming either. One file per run makes every pending review durable
regardless of how many other chains are started afterward.

Old files are swept on the next `run_live()` call, past a generous age, so a
demo session does not accumulate forever, but a review made minutes ago is
never at risk of being cleaned up mid-decision."""

MAX_LIVE_DB_AGE_SECONDS = 3600
"""An hour is far longer than any single demo session's pending review would
realistically sit unconfirmed, and short enough that a forgotten laptop does
not accumulate these indefinitely."""

GROUP_ID = "simple_live_demo"
DISPLAY_NAME = "Demo student"

# Two department stories, not one. Robotics is the clean, confident pattern
# catch: nearly the whole cohort shares one exact misconception, so the
# system converges on "recurring" quickly and cleanly (see the module
# docstring for how each robotics chain was picked to minimise incidental
# overlap). Computer science is the honest contrast: no single misconception
# dominates the department (see docs/memory-demo-department-selection.md -
# three concepts tied at 10/14 students each), so the same real members as
# the verified mem_cs_erratic_dept identity produce genuine variety -
# "similar", "improving", "not enough evidence" - before ever claiming
# "recurring", which is exactly the point: the system does not force a
# pattern where the data does not clearly have one.
#
# CATEGORY is "A" for robotics (expected to converge) and "B" for CS
# (expected to stay honestly uncertain, at least for the shorter chains) -
# same category meaning as the rest of the memory demo
# (docs/memory-demo-manifest.json).
DEPARTMENTS = {
    "robotics": {"category": "A", "label": "Robotics - clean pattern"},
    "computer_science": {"category": "B", "label": "Computer science - erratic"},
}

# See the module docstring (robotics) and
# docs/memory-demo-department-selection.md (computer science) for how each
# chain was chosen and verified. Keyed by (department, length).
CHAINS: dict[tuple[str, int], list[str]] = {
    ("robotics", 2): ["stu_76d01d7712", "stu_c70717f485"],           # Harshavaradhan G, Krish
    ("robotics", 3): ["stu_dfa174a2db", "stu_fd49dd9cfd",            # Sathya Sa, JYOTHISH,
                       "stu_c70717f485"],                            # Krish
    ("robotics", 4): ["stu_dfa174a2db", "stu_fd49dd9cfd",            # + N.karthikeyn
                       "stu_93dfa11827", "stu_c70717f485"],

    # Same real members, same order, as mem_cs_erratic_dept's first N -
    # already verified (docs/memory-demo-department-selection.md) to produce
    # real variety rather than a forced "recurring".
    ("computer_science", 2): ["stu_f834cd4135", "stu_2bf3073f73"],   # Anbuselvan, MONISH
    ("computer_science", 3): ["stu_f834cd4135", "stu_2bf3073f73",
                               "stu_c744ac76e6"],                    # + Harshavardhan K
    ("computer_science", 4): ["stu_f834cd4135", "stu_2bf3073f73",
                               "stu_c744ac76e6", "stu_6c627f5ddc"],  # + Rafan M A
}


def _db_path(session_id: str) -> Path:
    return LIVE_DB_DIR / f"{session_id}.db"


def _sweep_old_dbs() -> None:
    """Remove session databases past MAX_LIVE_DB_AGE_SECONDS. Called at the
    start of every run_live(), so a long-forgotten demo session cleans up
    without needing its own scheduled job, and never touches a file young
    enough to hold a review someone might still be about to act on."""
    if not LIVE_DB_DIR.exists():
        return
    cutoff = time.time() - MAX_LIVE_DB_AGE_SECONDS
    for p in LIVE_DB_DIR.glob("*.db*"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass  # another process/session touching it - leave it alone


def _new_session_store() -> tuple[str, Store]:
    """A fresh session id and its own database file - never shared with any
    other run, so an earlier run's pending review is never at risk from a
    later one."""
    _sweep_old_dbs()
    LIVE_DB_DIR.mkdir(parents=True, exist_ok=True)
    session_id = uuid.uuid4().hex[:12]
    db_path = _db_path(session_id)
    shutil.copy(SOURCE_DB, db_path)
    return session_id, Store(db_path)


def _build_chain(src: sqlite3.Connection, store: Store, members: list[str],
                  department: str) -> list[dict]:
    """N runs, same shape build_memory_demo.build() produces, minus the parts
    (validate(), multi-department checks) that only matter for a full
    6-member group. Reuses attempt_for()/read_sitting() unchanged - the same
    functions that build every other identity in this project."""
    category = DEPARTMENTS[department]["category"]
    group = {"id": GROUP_ID, "display": DISPLAY_NAME,
             "department": department, "category": category}
    sittings = []
    for i, member in enumerate(members, start=1):
        data = read_sitting(src, member)
        when = FIRST_SITTING + timedelta(weeks=WEEKS_BETWEEN * (i - 1))
        attempt = attempt_for(group, i, when, data)
        run_id = store.create_run("recall", meta={
            "student_id": group["id"], "display_name": DISPLAY_NAME,
            "department": department, "category": category, "sitting": i,
            "synthetic_timeline": True, "replayed_from_real_student": member,
        })
        store.set_state(run_id, RunState.NEW_ATTEMPT)
        store.append(run_id, "attempt", attempt, produced_by="ingest:replay")

        # created_at drives history.py's ordering, so it has to reflect the
        # fabricated calendar, not the moment this ran - same reasoning as
        # build_memory_demo.build().
        store.db.execute(
            "UPDATE runs SET created_at=?, updated_at=? WHERE id=?",
            (time.mktime(when.timetuple()),) * 2 + (run_id,))

        sittings.append({
            "sitting": i, "run_id": run_id, "date": when.isoformat(),
            "real_student_id": member,
            "real_student_name": data["student"]["name"],
            "score": attempt["quiz_meta"]["score"],
        })
    store.db.commit()
    return sittings


_REF_RE = re.compile(r"\b([a-z]{2}_t\d+_q\d+)(#[A-D])?\b")
"""Matches a raw question reference like rb_t1_q2 or rb_t1_q2#B - the internal
id, not something a judge should ever have to read. Used both to build the
plain citation line and to scrub the model's own free-text explanation,
which sometimes repeats these ids verbatim (it was given them as evidence)."""


def _plain_topic(qid: str) -> str:
    """'rb_t1_q2' -> 'Working out where the robot ends up' - the concept the
    question tests, not its internal id. Falls back to the id itself if the
    bank doesn't recognise it (should not happen for real question refs)."""
    try:
        q = bank.by_id(qid)
        return q.concept[0].upper() + q.concept[1:]
    except KeyError:
        return qid


def _humanise(text: str | None) -> str | None:
    """Replace every raw question reference in free text with its plain
    concept name, so the model's own explanation reads like something a
    judge can follow without a key to the id scheme."""
    if not text:
        return text
    return _REF_RE.sub(lambda m: _plain_topic(m.group(1)), text)


def _cited_topics(refs: list[str]) -> list[str]:
    seen: list[str] = []
    for ref in refs:
        m = _REF_RE.match(ref)
        label = _plain_topic(m.group(1)) if m else ref
        if label not in seen:
            seen.append(label)
    return seen


def run_live(settings, complete, notes: str, department: str = "robotics",
             length: int = 2) -> dict:
    """Build a fresh chain of `length` real sittings in `department`, advance
    every sitting but the last quietly, advance the last for real and time
    it, and return exactly what the simple page needs: one verdict, one
    citation, one plain sentence, how long the real call took, and - if the
    system paused - enough to render a real Confirm/Reject a teacher can
    act on.
    """
    if department not in DEPARTMENTS:
        raise ValueError(f"unknown department {department!r}; have {sorted(DEPARTMENTS)}")
    key = (department, length)
    if key not in CHAINS:
        lengths = sorted(l for d, l in CHAINS if d == department)
        raise ValueError(f"no verified {department} chain of length {length}; have {lengths}")
    members = CHAINS[key]

    session_id, store = _new_session_store()
    src_ro = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
    src_ro.row_factory = sqlite3.Row
    try:
        sittings = _build_chain(src_ro, store, members, department)
    finally:
        src_ro.close()

    flow = build_flow(call=complete, notes=notes)

    # Every sitting but the last: nothing new to watch happen. Advanced but
    # not narrated or timed - already true before the button was hit.
    for s in sittings[:-1]:
        advance(store, s["run_id"], flow, settings)

    # The last sitting: this is the real, timed, first-time model call.
    last = sittings[-1]
    started = time.time()
    state = advance(store, last["run_id"], flow, settings)
    elapsed = time.time() - started

    comparison = store.latest(last["run_id"], "comparison") or {}
    finding = store.latest(last["run_id"], "finding") or {}

    pending_question_id = None
    pending_question_text = None
    if state is RunState.NEEDS_REVIEW:
        pending = callback.pending(store, last["run_id"])
        if pending:
            pending_question_id = pending[0].id
            pending_question_text = pending[0].question

    return {
        "session_id": session_id,
        "run_id": last["run_id"],
        "seconds": round(elapsed, 1),
        "department": department,
        "department_label": DEPARTMENTS[department]["label"],
        "length": length,
        "sittings": [
            {"student_name": s["real_student_name"], "score": s["score"]}
            for s in sittings
        ],
        "label": comparison.get("label"),
        "explanation": _humanise(comparison.get("explanation")),
        "cited_topics": _cited_topics(comparison.get("related_refs") or []),
        "statement": _humanise(finding.get("statement")),
        "paused_for_human": state is RunState.NEEDS_REVIEW,
        "pending_question_id": pending_question_id,
        "pending_question_text": _humanise(pending_question_text),
    }


def decide(session_id: str, run_id: str, question_id: str, decision: str,
           settings, complete, notes: str) -> dict:
    """A teacher's real action on a pending review: 'confirm' or 'reject'.

    Writes the answer through the same slice.callback.answer() every other
    human-in-the-loop decision in this project goes through, then advances
    the run the rest of the way (RECORD_UPDATED -> RECOMMENDATION_READY),
    exactly as app/flow.py's handle_record_updated()/_classify_answer()
    already define - nothing here is a demo-only shortcut.

    `session_id` picks the SAME per-run database run_live() built this run
    in - each session has its own file (see LIVE_DB_DIR), so deciding on an
    older run is never at risk from a newer run_live() call in between.
    """
    if decision not in ("confirm", "reject"):
        raise ValueError(f"decision must be 'confirm' or 'reject', got {decision!r}")

    db_path = _db_path(session_id)
    if not db_path.exists():
        raise FileNotFoundError(
            f"no such demo session {session_id!r} - it may have been swept "
            f"after {MAX_LIVE_DB_AGE_SECONDS}s, or the server restarted")

    store = Store(db_path)
    callback.answer(store, question_id, decision, who="teacher")
    flow = build_flow(call=complete, notes=notes)
    advance(store, run_id, flow, settings)
    store.db.commit()

    finding = store.latest(run_id, "finding") or {}
    review = store.latest(run_id, "review") or {}
    return {
        "decision": decision,
        "finding_status": finding.get("status"),
        "review_decision": review.get("decision"),
    }
