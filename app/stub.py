"""Canned model responses, so the whole state machine runs with no key, no
network and no tokens.

This is phase 1, and it is worth doing first: the two-encounter story, the
negative control and the backwards arrow all demonstrable before a single real
model call exists. It is also what you fall back to on stage when the venue
wifi dies.

The stub is deliberately dumb - it matches on the step name and on what is
already in the store, and returns a fixed record. It is not a simulation of a
model and it should never grow into one.
"""
from __future__ import annotations

from .schema import Check, Comparison, Evidence, EvidenceSet, Finding

# --------------------------------------------------------------- the answers

_MIRA_1_EVIDENCE = EvidenceSet(
    items=[
        Evidence(concept="relating loop structure to growth rate", kind="strength",
                 passage="The outer loop runs n times.",
                 source_ref="assignment_1#response"),
        Evidence(concept="counting work inside loops", kind="difficulty",
                 passage="So insertion sort is O(n).",
                 source_ref="assignment_1#response"),
        Evidence(concept="justifying complexity claims from course material",
                 kind="difficulty",
                 passage="Insertion sort is the fastest sorting algorithm for all inputs.",
                 source_ref="assignment_1#response"),
    ],
    uncertainty_notes=["The claim that insertion sort is fastest for all inputs does "
                       "not appear in the lecture notes."],
)

_MIRA_2_EVIDENCE = EvidenceSet(
    items=[
        Evidence(concept="relating loop structure to growth rate", kind="strength",
                 passage="The loop goes through the list once, which is n steps.",
                 source_ref="assignment_2#response"),
        Evidence(concept="counting work inside loops", kind="difficulty",
                 passage="So removing duplicates is O(n).",
                 source_ref="assignment_2#response"),
    ],
    uncertainty_notes=[],
)

_ARUN_1_EVIDENCE = EvidenceSet(
    items=[
        Evidence(concept="counting work inside loops", kind="strength",
                 passage="the inner loop may shift up to n items",
                 source_ref="assignment_1#response"),
        Evidence(concept="justifying complexity claims from course material",
                 kind="difficulty",
                 passage="Insertion sort is O(n^2)",
                 source_ref="assignment_1#response"),
    ],
    uncertainty_notes=["The answer does not reference the lecture notes."],
)

_ARUN_3_EVIDENCE = EvidenceSet(
    items=[
        Evidence(concept="relating loop structure to growth rate", kind="difficulty",
                 passage="so it's O(n) because there's still a loop",
                 source_ref="assignment_3#response"),
    ],
    uncertainty_notes=[],
)


def _evidence_for(attempt: dict) -> EvidenceSet:
    key = (attempt["student_id"], attempt["assignment_id"])
    return {
        ("mira", "assignment_1"): _MIRA_1_EVIDENCE,
        ("mira", "assignment_2"): _MIRA_2_EVIDENCE,
        ("arun", "assignment_1"): _ARUN_1_EVIDENCE,
        ("arun", "assignment_3"): _ARUN_3_EVIDENCE,
    }[key]


def make_stub(store, run_id_holder):
    """Return a `call`-shaped function. `run_id_holder` is a one-element list so
    the demo can tell the stub which run it is answering for."""

    def call(*, settings, budget, messages, schema, step, **kw):
        run_id = run_id_holder[0]
        attempt = store.latest(run_id, "attempt")

        if step == "extract":
            return _evidence_for(attempt)

        if step == "compare":
            return _compare(store, run_id, attempt)

        if step == "finding":
            return _finding(store, run_id, attempt)

        if step == "check":
            return _check(store, run_id)

        raise AssertionError(f"stub has no answer for step {step!r}")

    return call


def _compare(store, run_id, attempt) -> Comparison:
    from . import history
    prior = history.prior_records(store, attempt["student_id"], run_id)
    if not prior["evidence"]:
        return Comparison(label="not_enough_evidence", related_refs=[],
                          explanation="No prior attempt for these learning objectives.")

    if attempt["student_id"] == "mira":
        return Comparison(
            label="recurring",
            related_refs=["assignment_1#response", "assignment_2#response"],
            explanation=("Assignment 1: counted only the outer loop of insertion sort. "
                         "Assignment 2: counted only the loop, ignoring the membership "
                         "check inside it."),
        )

    # Arun. Surface-similar to Mira's difficulty, unrelated to his own history.
    return Comparison(
        label="similar",
        related_refs=["assignment_1#response"],
        explanation=("Both answers make a complexity claim about a loop, but the "
                     "earlier difficulty was not justifying the claim against the "
                     "notes, and this one is not accounting for halving. Surface "
                     "similarity only; not the same difficulty."),
    )


def _finding(store, run_id, attempt) -> Finding:
    comparison = store.latest(run_id, "comparison")
    drafted = len(store.history(run_id, "finding"))

    if comparison["label"] == "recurring" and drafted == 0:
        # Deliberately overstated, so the checker has something real to reject.
        return Finding(revision=1, status="candidate_recurring",
                       statement="Mira does not understand time complexity.",
                       supporting_refs=[], uncertainty="", proposed_next_step="")

    if comparison["label"] == "recurring":
        return Finding(
            revision=2, status="candidate_recurring",
            statement=("A possible recurring difficulty in accounting for work done "
                       "inside a loop. In two assignments, the student counted only "
                       "the outer loop."),
            supporting_refs=["assignment_1#response", "assignment_2#response"],
            uncertainty="Two tasks only; professor review needed before intervention.",
            proposed_next_step=("Trace a nested loop by hand, count its operations for "
                                "n = 4 and n = 8, then state the growth rate."),
        )

    ref = f"{attempt['assignment_id']}#response"
    return Finding(
        revision=1, status="first_signal",
        statement=("In this response, the student made a complexity claim without "
                   "accounting for all the work the algorithm does."),
        supporting_refs=[ref],
        uncertainty="Single observation; recurrence not established.",
        proposed_next_step="None yet.",
    )


def _check(store, run_id) -> Check:
    finding = store.latest(run_id, "finding")
    if "does not understand" in finding["statement"]:
        return Check(verdict="rejected", failed_check="claim_strength",
                     detail=("The statement is stronger than the evidence and "
                             "describes the student, not the work."))
    comparison = store.latest(run_id, "comparison")
    if comparison["label"] == "recurring":
        return Check(verdict="needs_review", failed_check=None,
                     detail="Supported, but a recurring pattern is consequential.")
    return Check(verdict="accepted", failed_check=None, detail="")
