"""A read-only JSON view of the persistent-memory demo, for the mobile app.

The Flutter app needs to show the same thing the terminal demo shows: one
student identity, several sittings over time, and what the agent concluded on
each - including the sittings where it concluded nothing.

Three rules this module is built around.

**It states what happened, never why.** Every field here is a record the agent
actually wrote: the label it chose, the answers it cited, whether it paused for
a human. There is no field for "why this went wrong" and there should not be,
because a person is going to explain that out loud while the screen is showing
it. A screen that editorialises either steals that explanation or contradicts
it.

**It is read-only.** No route here writes anything. The demo database is built
by tools/build_memory_demo.py and replayed by tools/run_memory_demo.py; this
only reads what those left behind. A phone in someone's hand during a demo must
not be able to change the thing being demonstrated.

**It reads the database, not a transcript.** Everything comes out of the
`versions` table that the real pipeline wrote - the same rows app/history.py
reads. A JSON file exported alongside the run would be a second source of truth
and could drift from what the agent actually recorded.

Mounted by webapp.py at /api/memory, pointed at memory.db, which is separate
from the live webapp.db the quiz writes to.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/memory", tags=["memory"])

DB = Path(__file__).parent.parent / "memory.db"

# Which labels count as the agent having found something. Kept here as data
# rather than spelled out at each call site, so the app and any future caller
# agree on what "found a pattern" means.
FOUND = {"recurring"}


def _db() -> sqlite3.Connection:
    """A read-only connection. The demo is never written to over HTTP."""
    if not DB.exists():
        raise HTTPException(
            status_code=503,
            detail=("memory.db has not been built yet - run "
                    "tools/build_memory_demo.py, then tools/run_memory_demo.py"),
        )
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _latest(con: sqlite3.Connection, run_id: str, kind: str) -> dict[str, Any] | None:
    row = con.execute(
        "SELECT payload_json FROM versions WHERE run_id=? AND kind=?"
        " ORDER BY seq DESC LIMIT 1", (run_id, kind)).fetchone()
    return json.loads(row["payload_json"]) if row else None


def _runs(con: sqlite3.Connection, student_id: str | None = None) -> list[dict]:
    """Synthetic-identity runs, oldest first - the order the sittings happened."""
    out = []
    for r in con.execute(
            "SELECT id, state, created_at, meta_json FROM runs"
            " WHERE domain='recall' ORDER BY created_at"):
        meta = json.loads(r["meta_json"])
        if not meta.get("synthetic_timeline"):
            continue
        if student_id and meta.get("student_id") != student_id:
            continue
        out.append({"run_id": r["id"], "state": r["state"], "meta": meta})
    return out


def _sitting(con: sqlite3.Connection, run: dict) -> dict[str, Any]:
    """One sitting, as the app draws it.

    `outcome` is the single word the app keys its UI off. It reports the shape
    of the result and nothing beyond it:

        found       - the agent identified a repeat and cited it
        none_found  - the agent looked and did not claim one
        first       - nothing to compare against yet, this is sitting one
    """
    run_id = run["run_id"]
    attempt = _latest(con, run_id, "attempt") or {}
    comparison = _latest(con, run_id, "comparison") or {}
    finding = _latest(con, run_id, "finding") or {}
    check = _latest(con, run_id, "check") or {}
    meta = run["meta"]

    label = comparison.get("label")
    if label in FOUND:
        outcome = "found"
    elif label == "not_enough_evidence" and not comparison.get("related_refs"):
        outcome = "first"
    elif label is None:
        outcome = "first"
    else:
        outcome = "none_found"

    quiz = attempt.get("quiz_meta", {})
    return {
        "sitting": meta.get("sitting"),
        "run_id": run_id,
        "date": attempt.get("date"),
        "assignment_id": attempt.get("assignment_id"),
        "score": quiz.get("score"),
        "asked": quiz.get("asked"),

        # What the agent concluded. Its own words, unedited.
        "outcome": outcome,
        "label": label,
        "explanation": comparison.get("explanation"),
        "cited_answers": comparison.get("related_refs") or [],

        # What it could see when it decided. This is the persistence itself:
        # sitting 1 sees nothing, later sittings see the ones before them.
        # Filled by the caller, which knows this sitting's position in the run.
        "prior_sittings_visible": max((meta.get("sitting") or 1) - 1, 0),
        "finding": ({
            "status": finding.get("status"),
            "statement": finding.get("statement"),
            "uncertainty": finding.get("uncertainty"),
            "next_step": finding.get("proposed_next_step"),
            "cites": finding.get("supporting_refs") or [],
        } if finding else None),

        # Who decides. `awaiting_human` true means the agent stopped and handed
        # the call to a professor rather than closing the record itself.
        "checked": check.get("verdict"),
        "awaiting_human": run["state"] == "needs_review",
        "state": run["state"],

        # Provenance, on every sitting, so the app can always show it.
        "real_answers_from": quiz.get("replayed_from_real_name"),
        "real_student_id": quiz.get("replayed_from_real_student"),
        "synthetic_timeline": True,
    }


DISCLOSURE = (
    "Every answer in this record is a real answer from a real student who took "
    "this quiz. The timeline is constructed: separate real students are shown "
    "here as one person sitting the quiz several times, because the system "
    "detects mistakes that repeat across separate occasions and a two-day event "
    "cannot produce that naturally."
)
"""Served with every response, so the app cannot display this data without
having been handed the disclosure to put on screen."""


@router.get("/students")
def students() -> dict[str, Any]:
    """Every synthetic identity, for the app's list screen."""
    con = _db()
    try:
        groups: dict[str, dict] = {}
        for run in _runs(con):
            meta = run["meta"]
            sid = meta.get("student_id")
            g = groups.setdefault(sid, {
                "student_id": sid,
                "name": meta.get("display_name"),
                "department": meta.get("department"),
                "sittings": 0,
                "found_a_repeat": False,
                "awaiting_human": False,
            })
            g["sittings"] += 1
            s = _sitting(con, run)
            if s["outcome"] == "found":
                g["found_a_repeat"] = True
            if s["awaiting_human"]:
                g["awaiting_human"] = True
        return {"students": list(groups.values()), "disclosure": DISCLOSURE}
    finally:
        con.close()


@router.get("/student/{student_id}")
def student(student_id: str) -> dict[str, Any]:
    """One identity's full history - the screen the demo lives on.

    Sittings come back oldest first. Read down the list and the persistence is
    the story: the first sitting has nothing behind it, and each later one is
    deciding against everything before it.
    """
    con = _db()
    try:
        runs = _runs(con, student_id)
        if not runs:
            raise HTTPException(status_code=404, detail=f"no such identity: {student_id}")

        sittings = [_sitting(con, r) for r in runs]
        for i, s in enumerate(sittings):
            s["prior_sittings_visible"] = i     # what this sitting could see

        meta = runs[0]["meta"]
        return {
            "student_id": student_id,
            "name": meta.get("display_name"),
            "department": meta.get("department"),
            "sittings": sittings,
            "summary": {
                "total_sittings": len(sittings),
                "repeats_found": sum(1 for s in sittings if s["outcome"] == "found"),
                "no_repeat_claimed": sum(1 for s in sittings
                                         if s["outcome"] == "none_found"),
                "awaiting_human": sum(1 for s in sittings if s["awaiting_human"]),
            },
            "disclosure": DISCLOSURE,
        }
    finally:
        con.close()


@router.get("/sitting/{run_id}")
def sitting(run_id: str) -> dict[str, Any]:
    """One sitting in full, including the answers the agent cited.

    The citations are the point of this route. A claim on screen next to the
    actual answers it rests on is checkable by whoever is watching; the same
    claim on its own is just an assertion.
    """
    con = _db()
    try:
        run = next((r for r in _runs(con) if r["run_id"] == run_id), None)
        if run is None:
            raise HTTPException(status_code=404, detail=f"no such sitting: {run_id}")

        body = _sitting(con, run)
        attempt = _latest(con, run_id, "attempt") or {}
        evidence = _latest(con, run_id, "evidence") or {}

        body["answers"] = [{
            "ref": i.get("source_ref"),
            "concept": i.get("concept"),
            "kind": i.get("kind"),          # strength | difficulty
            "detail": i.get("note"),
            "cited_here": i.get("source_ref") in set(body["cited_answers"]),
        } for i in evidence.get("items", [])]

        body["prompt"] = attempt.get("assignment_prompt")
        body["disclosure"] = DISCLOSURE
        return body
    finally:
        con.close()
