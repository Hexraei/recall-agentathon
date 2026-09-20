"""A read-only JSON view of the individual student report, for the mobile app.

The web app already has this report - `GET /report/{sid}` in webapp.py renders
it as HTML for a student reading their own result in a browser. The Flutter
app needs the same information, not a re-derivation of it, so this module
does exactly one thing: it calls the existing `report.for_student()` (the
real agent pipeline - facts pulled from the quiz answers, four model calls
that draft, correct and check the wording, same as the web page uses) and
serialises its return dict as JSON instead of HTML.

Two rules this module is built around, matching app/memory_api.py.

**It is read-only.** No route here writes anything new. `report.for_student()`
itself may write a cache row on first generation - that is the underlying
pipeline's existing behaviour, unchanged by exposing it as JSON, and the same
thing the HTML route already does on every request.

**It states what happened, never why.** The response carries whatever
`for_student()` produced - headline, strengths, gaps, next step - plus the
same provenance flags the HTML page shows: `_from_cache` (a database read, no
model call, vs. freshly generated) and `_unverified` (the wording has not
been signed off by the checker, though the numbers behind it are accurate).
Neither is reworded or explained here; the app shows them plainly, same as
the HTML page does.

Mounted by webapp.py at /api/report, reading the same webapp.db the quiz
writes to - unlike memory_api.py, which reads the separate, static memory.db.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app import report, roster
from slice.llm import ModelError, complete

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{student_id}")
def student_report(student_id: str, force: int = 0) -> dict[str, Any]:
    """The consolidated report for one student, as JSON.

    Wraps `report.for_student()` exactly - same facts, same four-step agent
    trail, same cache. `force=1` regenerates it, the same escape hatch the
    HTML route offers for a demo that needs to show the agent run live.

    Returns 404 if the student does not exist or has not answered anything
    yet (there is nothing for the agent to read). Returns 503, not a crash,
    if the model that writes the report cannot be reached - the same failure
    the HTML route's `_model_error_page` handles, here as a plain JSON body
    instead of a styled page.
    """
    from webapp import _settings, store  # local import: avoids a circular

    s = store()
    stu = roster.student(s, student_id)
    if not stu:
        raise HTTPException(status_code=404, detail=f"no such student: {student_id}")

    got, asked = roster.score(s, student_id)
    if asked == 0:
        raise HTTPException(
            status_code=404,
            detail=f"{student_id} has not answered any questions yet",
        )

    try:
        body = report.for_student(s, student_id, _settings, call=complete,
                                  force=bool(force))
    except ModelError as e:
        raise HTTPException(
            status_code=503,
            detail=("The report could not be generated - the model that "
                    f"writes it is unreachable right now: {e}"),
        )

    # The student's own identity and raw score, alongside the agent's report -
    # the app needs both to render the same header the HTML page shows.
    body["student_id"] = student_id
    body["name"] = stu["name"]
    body["department"] = stu["department"]
    body["register_no"] = stu["register_no"]
    body["score"] = got
    body["asked"] = asked
    body["by_topic"] = roster.by_topic(s, student_id)
    return body
