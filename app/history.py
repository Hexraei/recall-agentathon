"""Reading one student's earlier runs.

Each submission is its own run. A later submission starts a NEW run that reads
earlier runs' records for the same student - no finished run is ever resumed.
This module is the only place that reads across runs, and it is what the second
encounter depends on. Delete these records and encounter 2 must fall back to
`not_enough_evidence`; that is the check a judge will ask for.
"""
from __future__ import annotations

from typing import Any

from slice.store import Store


def _runs_for(store: Store, student_id: str, before_run: str) -> list[str]:
    """Earlier run ids for this student, oldest first.

    Ordered by created_at, and `before_run` is excluded so a run never reads
    itself as its own history.
    """
    rows = store.db.execute(
        "SELECT id, meta_json FROM runs WHERE id != ? ORDER BY created_at",
        (before_run,),
    ).fetchall()
    out = []
    for r in rows:
        import json
        if json.loads(r["meta_json"]).get("student_id") == student_id:
            out.append(r["id"])
    return out


def prior_records(store: Store, student_id: str, before_run: str) -> dict[str, list[dict[str, Any]]]:
    """Every evidence, finding and review this student has from earlier runs.

    Returns them grouped by kind, each row tagged with the run and assignment it
    came from so a comparison can cite it.

    Note this walks `history`, not `latest`. Evidence and findings are written
    many times per run; `latest` would hand back whichever row happened to be
    written last, about whichever item.
    """
    out: dict[str, list[dict[str, Any]]] = {"evidence": [], "finding": [], "review": []}
    for run_id in _runs_for(store, student_id, before_run):
        attempt = store.latest(run_id, "attempt") or {}
        assignment = attempt.get("assignment_id", "unknown")
        for kind in out:
            for version in store.history(run_id, kind):
                out[kind].append({
                    "run_id": run_id,
                    "assignment_id": assignment,
                    "date": attempt.get("date"),
                    **version.payload,
                })
    return out


def is_duplicate(store: Store, student_id: str, assignment_id: str, before_run: str) -> bool:
    """Has this student already submitted this assignment?

    A duplicate submission would later look like a second encounter and fake a
    recurrence, so it is stopped at ingest rather than discovered in a finding.
    """
    for run_id in _runs_for(store, student_id, before_run):
        attempt = store.latest(run_id, "attempt")
        if attempt and attempt.get("assignment_id") == assignment_id:
            return True
    return False
