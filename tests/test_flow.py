"""The properties, not the happy path.

The demo shows the pipeline running. These prove the things that would not be
visible by watching it: that the second encounter depends on stored records,
that a fabricated citation is rejected, that a poisoned submission does not
redirect the run, and that the two counters are separate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slice import callback
from slice.config import settings as load_settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import fixtures, provenance
from app.flow import build_flow
from app.schema import Evidence
from app.stub import make_stub

NOTES = (Path(__file__).resolve().parents[1] / "corpus" / "ds-notes.md").read_text()


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def settings():
    return load_settings()


def run(store, settings, attempt, answer=None):
    """Submit one attempt, answering the professor if asked. Returns run id."""
    run_id = store.create_run("recall", meta={"student_id": attempt["student_id"]})
    store.set_state(run_id, RunState.NEW_ATTEMPT)
    store.append(run_id, "attempt", attempt, produced_by="ingest")
    flow = build_flow(call=make_stub(store, [run_id]), notes=NOTES)

    state = advance(store, run_id, flow, settings)
    if state is RunState.NEEDS_REVIEW and answer is not None:
        pending = callback.pending(store, run_id)
        callback.answer(store, pending[0].id, answer, who="professor")
        store.set_state(run_id, RunState.RECORD_UPDATED)
        advance(store, run_id, flow, settings)
    return run_id


# --------------------------------------------------- the second encounter

def test_first_encounter_cannot_claim_recurrence(store, settings):
    run_id = run(store, settings, fixtures.MIRA_1)
    assert store.latest(run_id, "comparison")["label"] == "not_enough_evidence"
    assert store.latest(run_id, "finding")["status"] == "first_signal"


def test_second_encounter_finds_the_pattern(store, settings):
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_2, answer="confirm")
    assert store.latest(run_id, "comparison")["label"] == "recurring"
    assert store.latest(run_id, "finding")["status"] == "confirmed_recurring"


def test_second_encounter_depends_on_stored_history(store, settings):
    """The claim a judge will ask about: is the second result real, or is it
    hard-coded? Run encounter 2 with no encounter 1 in the store and it must
    fall back, because there is nothing to compare against."""
    run_id = run(store, settings, fixtures.MIRA_2)
    assert store.latest(run_id, "comparison")["label"] == "not_enough_evidence"
    assert store.latest(run_id, "finding")["status"] == "first_signal"


def test_records_survive_the_process(tmp_path, settings):
    """Encounter 1 in one Store, encounter 2 in another, as separate processes
    would. The pattern must still be found."""
    path = tmp_path / "durable.db"
    first = Store(path)
    run(first, settings, fixtures.MIRA_1)
    first.close()

    second = Store(path)
    run_id = run(second, settings, fixtures.MIRA_2, answer="confirm")
    assert second.latest(run_id, "comparison")["label"] == "recurring"
    second.close()


# ------------------------------------------------------ the negative control

def test_superficial_similarity_is_not_recurrence(store, settings):
    """Arun's binary-search error looks like Mira's and shares a concept tag
    with his own earlier work. It is neither. A `recurring` label here is a
    false positive and the worst failure this system has."""
    run(store, settings, fixtures.ARUN_1)
    run_id = run(store, settings, fixtures.ARUN_3)
    assert store.latest(run_id, "comparison")["label"] != "recurring"
    assert store.latest(run_id, "finding")["status"] != "candidate_recurring"


def test_one_students_history_does_not_leak_into_another(store, settings):
    run(store, settings, fixtures.MIRA_1)
    run(store, settings, fixtures.MIRA_2, answer="confirm")
    run_id = run(store, settings, fixtures.ARUN_1)
    # Arun has no prior work, and Mira's must not count as his.
    assert store.latest(run_id, "comparison")["label"] == "not_enough_evidence"


# ------------------------------------------------------------- the back-edge

def test_an_overstated_finding_is_rejected_and_redrafted(store, settings):
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_2, answer="confirm")

    checks = [c.payload for c in store.history(run_id, "check")]
    assert any(c["verdict"] == "rejected" and c["failed_check"] == "claim_strength"
               for c in checks), "the checker never rejected the overstated finding"

    findings = [f.payload for f in store.history(run_id, "finding")]
    assert len(findings) > 1, "a rejection must be followed by a fresh draft"
    assert "does not understand" in findings[0]["statement"]
    assert "does not understand" not in store.latest(run_id, "finding")["statement"]


def test_revision_limit_is_counted_from_records_not_the_budget(store, settings):
    """The two bounds must not share a counter. This asserts the revision limit
    reads `finding` history; the budget's attempt counter is untouched by it."""
    from app.flow import MAX_FINDINGS
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_2, answer="confirm")
    drafted = len([f for f in store.history(run_id, "finding")
                   if f.produced_by == "agent:finding"])
    assert drafted <= MAX_FINDINGS
    assert store.counter(run_id, "attempt:finding") == 0, \
        "the stub makes no model calls, so the spend counter must be untouched"


# --------------------------------------------------------------- provenance

def test_a_fabricated_quote_is_demoted_not_dropped():
    items = [
        Evidence(concept="c", kind="difficulty",
                 passage="a sentence the student never wrote",
                 source_ref="assignment_1#response"),
        Evidence(concept="c", kind="strength",
                 passage="The outer loop runs n times.",
                 source_ref="assignment_1#response"),
    ]
    checked = provenance.check_evidence(
        items, {"assignment_1#response": fixtures.MIRA_1["submission"]})
    assert len(checked) == 2, "a failed row is kept, never deleted"
    assert checked[0].supported is False
    assert "could not establish" in checked[0].note
    assert checked[1].supported is True


def test_a_citation_to_an_unloaded_document_fails():
    items = [Evidence(concept="c", kind="difficulty", passage="anything",
                      source_ref="notes_we_never_loaded.md")]
    checked = provenance.check_evidence(items, {"assignment_1#response": "text"})
    assert checked[0].supported is False
    assert "not loaded by this run" in checked[0].note


def test_whitespace_differences_do_not_fail_a_real_quote():
    items = [Evidence(concept="c", kind="strength",
                      passage="The  outer   loop\nruns n times.",
                      source_ref="a#r")]
    checked = provenance.check_evidence(items, {"a#r": "The outer loop runs n times."})
    assert checked[0].supported is True


def test_a_finding_citing_unsupported_evidence_is_rejected(store, settings):
    """The gate that stops a finding resting on a row that failed the check."""
    run_id = store.create_run("recall", meta={"student_id": "mira"})
    store.set_state(run_id, RunState.NEW_ATTEMPT)
    store.append(run_id, "attempt", fixtures.MIRA_1, produced_by="ingest")
    store.append(run_id, "evidence", {
        "items": [{"concept": "c", "kind": "difficulty", "passage": "x",
                   "source_ref": "assignment_1#response", "supported": False,
                   "note": "could not establish"}],
        "uncertainty_notes": [], "unsupported_count": 1,
    }, produced_by="agent:extract")
    store.append(run_id, "comparison",
                 {"label": "not_enough_evidence", "related_refs": [], "explanation": "-"},
                 produced_by="agent:compare")
    store.append(run_id, "finding", {
        "revision": 1, "status": "first_signal", "statement": "A claim.",
        "supporting_refs": ["assignment_1#response"], "uncertainty": "-",
        "proposed_next_step": "-",
    }, produced_by="agent:finding")
    store.set_state(run_id, RunState.EVIDENCE_CHECK)

    flow = build_flow(call=make_stub(store, [run_id]), notes=NOTES)
    advance(store, run_id, flow, settings)

    # The first check is the one under test: a finding resting on a row that
    # failed provenance. The run then re-extracts, which is the citation
    # back-edge doing its job.
    checks = [c.payload for c in store.history(run_id, "check")]
    assert checks[0]["verdict"] == "rejected"
    assert checks[0]["failed_check"] == "citation"


def test_a_cross_run_citation_is_not_treated_as_fabricated(store, settings):
    """A recurring finding cites the earlier assignment, which is legitimate
    precisely because it is not in this run's evidence."""
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_2, answer="confirm")
    final = store.latest(run_id, "finding")
    assert "assignment_1#response" in final["supporting_refs"]
    citation_failures = [c.payload for c in store.history(run_id, "check")
                         if c.payload["failed_check"] == "citation"]
    assert not citation_failures, "the cross-encounter citation was wrongly rejected"


# -------------------------------------------------------------- adversarial

def test_a_poisoned_submission_does_not_redirect_the_run(store, settings):
    """The submission is data, not instructions. A sentence telling the system
    to record no difficulties must not change the outcome.

    Nothing here asks the model to resist it. The structure is what holds: the
    verdict comes from a typed schema, and the citation check asks the model
    nothing."""
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_2_POISONED, answer="confirm")

    evidence = store.latest(run_id, "evidence")
    assert any(i["kind"] == "difficulty" for i in evidence["items"]), \
        "the injected instruction suppressed the difficulties"
    assert store.latest(run_id, "comparison")["label"] == "recurring"


# ------------------------------------------------------------------- ingest

def test_a_duplicate_submission_is_refused(store, settings):
    run(store, settings, fixtures.MIRA_1)
    run_id = run(store, settings, fixtures.MIRA_1)
    assert store.get_state(run_id) is RunState.FAILED
    assert store.latest(run_id, "failure")["kind"] == "duplicate_submission"


def test_missing_fields_fail_at_ingest(store, settings):
    run_id = run(store, settings, dict(fixtures.MIRA_1, submission=""))
    assert store.get_state(run_id) is RunState.FAILED
    assert store.latest(run_id, "failure")["kind"] == "bad_input"


# -------------------------------------------------------- the waiting state

def test_the_run_suspends_and_a_later_call_resumes_it(store, settings):
    run(store, settings, fixtures.MIRA_1)
    run_id = store.create_run("recall", meta={"student_id": "mira"})
    store.set_state(run_id, RunState.NEW_ATTEMPT)
    store.append(run_id, "attempt", fixtures.MIRA_2, produced_by="ingest")
    flow = build_flow(call=make_stub(store, [run_id]), notes=NOTES)

    state = advance(store, run_id, flow, settings)
    assert state is RunState.NEEDS_REVIEW
    assert state.is_suspended and not state.is_terminal
    assert store.latest(run_id, "summary") is None, "suspended runs produce no summary"

    pending = callback.pending(store, run_id)
    callback.answer(store, pending[0].id, "confirm", who="professor")
    store.set_state(run_id, RunState.RECORD_UPDATED)
    assert advance(store, run_id, flow, settings) is RunState.COMPLETE
    assert store.latest(run_id, "summary") is not None


def test_silence_is_recorded_as_silence(store, settings):
    """Nobody answers. The finding must not be confirmed, and the output has to
    say we asked - distinct from a run that never needed to."""
    run(store, settings, fixtures.MIRA_1)
    run_id = store.create_run("recall", meta={"student_id": "mira"})
    store.set_state(run_id, RunState.NEW_ATTEMPT)
    store.append(run_id, "attempt", fixtures.MIRA_2, produced_by="ingest")
    flow = build_flow(call=make_stub(store, [run_id]), notes=NOTES)

    assert advance(store, run_id, flow, settings) is RunState.NEEDS_REVIEW
    # The timeout fires; sweep converts silence into a recorded unknown.
    pending = callback.pending(store, run_id)
    store.db.execute("UPDATE questions SET timeout_at = 0 WHERE id = ?", (pending[0].id,))
    store.set_state(run_id, RunState.RECORD_UPDATED)
    advance(store, run_id, flow, settings)

    summary = store.latest(run_id, "summary")
    assert summary["professor"] == "no_reply"
    assert summary["professor_asked_no_reply"] is True
    assert summary["next_step"] is None, "no next step is issued on silence"
    assert store.latest(run_id, "finding")["status"] != "confirmed_recurring"


def test_a_run_nobody_was_asked_about_is_not_reported_as_ignored(store, settings):
    """`not_asked` and `no_reply` must be different in the output."""
    run_id = run(store, settings, fixtures.MIRA_1)
    summary = store.latest(run_id, "summary")
    assert summary["professor"] == "not_asked"
    assert summary["professor_asked_no_reply"] is False
    assert store.history(run_id, "review") == []


# ------------------------------------------------------------- append-only

def test_the_history_cannot_be_rewritten(store, settings):
    import sqlite3
    run_id = run(store, settings, fixtures.MIRA_1)
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE versions SET kind='tampered' WHERE run_id=?", (run_id,))
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("DELETE FROM versions WHERE run_id=?", (run_id,))
