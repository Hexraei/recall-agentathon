"""The handlers, the transitions, and the rules.

All the domain rules live here, in code, not in the prompts. The model returns
a judgement inside a step; this file decides what that judgement means and what
happens next.

The back-edge is the evidence check, and where it sends work back to depends on
WHY the check failed:

    citation            -> EXTRACTING   (the passages are wrong)
    claim_strength      -> COMPARING    (the reading of the evidence is wrong)
    comparison_validity -> COMPARING    (the comparison itself is wrong)

Nothing in slice/ changes for this to run, except the RunState enum, which
shipped with another domain's states baked into it.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from slice import callback
from slice.llm import complete, ModelError
from slice.records import RunState

from . import history, provenance
from . import jev_compare as jev
from .schema import Check, Comparison, EvidenceSet, Finding, Review

# --------------------------------------------------------------- domain rules

MAX_FINDINGS = 3
"""How many findings a run may draft before it stops looping and asks the
professor.

Counted from the `finding` records in the run's history - deliberately NOT from
budget.attempt(), which is a spend fence and is also ticking for retries after a
malformed response. Share one counter and two bad replies silently buy one
revision instead of three, which you find out on stage.
"""

RECURRENCE_NEEDS_ATTEMPTS = 2
"""What counts as recurring: evidence from at least this many DIFFERENT
assignments. A single mistake is not a recurring misconception.

This is a domain opinion, not architecture. The token ceiling, the attempts per
step and the review timeout are architecture; this number is a claim about
teaching and it is the one to argue about with a professor.
"""

_PROMPTS = Path(__file__).parent / "prompts"


def _prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ messages
# Templates, not model calls. Four model calls in this build - extract,
# compare, draft, and the claim-strength half of the check - and no ambiguity
# about which they are.

def build_extract_messages(attempt: dict, notes: str,
                           chunks: list | None = None) -> list[dict]:
    """`chunks` is what retrieval found for this submission. When it is None the
    whole `notes` string is sent, which is what happens with no corpus ingested.

    Sending everything does not scale and is not the point. Two pages of notes
    is 758 tokens to analyse a 29-token answer; a real course is fifty pages and
    simply will not fit. Retrieval also makes the citation check mean something
    here: a claim cites `ds-notes.md#3`, a passage a reader can open, rather than
    one undifferentiated blob called `course_notes`.
    """
    if chunks:
        material = "\n\n".join(f"[{c.cite()}]\n{c.text}" for c in chunks)
        header = ("Relevant course notes. Cite the reference in brackets as the "
                  "source_ref when a passage comes from one of these:")
    else:
        material = notes
        header = "Course notes (source_ref: course_notes):"

    return [
        {"role": "system", "content": _prompt("extract")},
        {"role": "user", "content": (
            f"Assignment prompt:\n{attempt['assignment_prompt']}\n\n"
            f"Learning objectives:\n" + "\n".join(f"- {o}" for o in attempt["learning_objectives"])
            + f"\n\n{header}\n{material}"
            + f"\n\nThe student's submission (source_ref: {attempt['assignment_id']}#response):\n"
            + attempt["submission"]
        )},
    ]


def build_compare_messages(evidence: dict, prior: dict, objectives: list[str]) -> list[dict]:
    return [
        {"role": "system", "content": _prompt("compare")},
        {"role": "user", "content": (
            "Learning objectives for this assignment:\n"
            + "\n".join(f"- {o}" for o in objectives)
            + "\n\nEvidence from the CURRENT submission:\n"
            + json.dumps(evidence, indent=2)
            + "\n\nThis student's EARLIER records:\n"
            + json.dumps(prior, indent=2)
        )},
    ]


def build_finding_messages(evidence: dict, comparison: dict,
                           attempt: dict, rejected: dict | None) -> list[dict]:
    user = [
        f"Assignment: {attempt['assignment_id']}",
        "Evidence:\n" + json.dumps(evidence, indent=2),
        "Comparison with history:\n" + json.dumps(comparison, indent=2),
    ]
    if rejected:
        # A targeted rewrite, not a blind retry. An identical second request
        # usually fails identically; showing the model its own rejected output
        # and the specific objection is what changes the outcome.
        user.append(
            "Your previous finding was REJECTED.\n"
            + json.dumps(rejected["finding"], indent=2)
            + f"\n\nFailed check: {rejected['failed_check']}\n"
            + f"Why: {rejected['detail']}\n\n"
            "Write a finding that survives that objection. Do not restate the "
            "rejected claim in softer words."
        )
    return [
        {"role": "system", "content": _prompt("finding")},
        {"role": "user", "content": "\n\n---\n\n".join(user)},
    ]


def build_check_messages(finding: dict, evidence: dict, comparison: dict) -> list[dict]:
    return [
        {"role": "system", "content": _prompt("check")},
        {"role": "user", "content": (
            "Finding under review:\n" + json.dumps(finding, indent=2)
            + "\n\nEvidence it must rest on:\n" + json.dumps(evidence, indent=2)
            + "\n\nComparison it must not overstate:\n" + json.dumps(comparison, indent=2)
        )},
    ]


# ------------------------------------------------------------------ handlers

def build_flow(call=complete, notes: str = "", trace=None):
    """Return the Flow.

    `call` is injected so the whole state machine can be exercised with canned
    responses - no key, no network, no tokens. That is phase 1: the two-encounter
    story and the backwards arrow, with no model involved.

    `trace` is an optional callable taking (step, seconds, detail). A real model
    call takes long enough that a silent terminal looks hung, and a run that
    looks hung is a run the audience stops believing in. Nothing here depends on
    it; pass None and the flow is unchanged.
    """
    import time as _time

    def timed(step: str, fn, detail=lambda r: ""):
        started = _time.time()
        result = fn()
        if trace:
            trace(step, _time.time() - started, detail(result))
        return result

    def handle_new_attempt(ctx) -> RunState:
        """Ingest. Normalise, and refuse a duplicate.

        A duplicate submission would later look like a second encounter and fake
        a recurrence, so it is stopped here rather than found in a finding.
        """
        attempt = ctx.latest("attempt")
        if attempt is None:
            ctx.append("failure",
                       {"kind": "no_attempt", "detail": "Run started with no attempt record."},
                       produced_by="ingest")
            return RunState.FAILED

        missing = [f for f in ("student_id", "assignment_id", "assignment_prompt",
                               "learning_objectives", "submission")
                   if not attempt.get(f)]
        if missing:
            ctx.append("failure",
                       {"kind": "bad_input",
                        "detail": "Missing required fields: " + ", ".join(missing)},
                       produced_by="ingest")
            return RunState.FAILED

        if history.is_duplicate(ctx.store, attempt["student_id"],
                                attempt["assignment_id"], ctx.run_id):
            ctx.append("failure",
                       {"kind": "duplicate_submission",
                        "detail": f"{attempt['student_id']} has already submitted "
                                  f"{attempt['assignment_id']}. A duplicate would fake "
                                  "a second encounter."},
                       produced_by="ingest")
            return RunState.FAILED

        return RunState.EXTRACTING

    def handle_extracting(ctx) -> RunState:
        """Pull evidence passages, then verify every citation in plain code."""
        attempt = ctx.latest("attempt")

        # MCQ submissions carry their evidence already, computed at
        # question-writing time (app/quiz.py) rather than inferred by a model
        # from a bare option letter. No model call, no citation check needed -
        # there is no passage to fabricate when nothing was extracted from
        # prose. See handle_new_attempt / app/quiz.py for why this is the
        # deliberate choice, not a shortcut.
        precomputed = attempt.get("precomputed_evidence")
        if precomputed is not None:
            ctx.append("evidence", precomputed, produced_by="quiz:lookup")
            return RunState.COMPARING

        # Retrieve the notes that bear on THIS submission, rather than sending
        # all of them. Falls back to the whole string if no corpus is ingested,
        # so the flow still runs with retrieval switched off.
        chunks = _retrieve_notes(ctx, attempt)

        result = timed("extract", lambda: call(
            settings=ctx.settings, budget=ctx.budget,
            messages=build_extract_messages(attempt, notes, chunks),
            schema=EvidenceSet, step="extract",
        ), lambda r: f"{len(r.items)} passages")

        # Only what this run actually loaded counts as a source. A retrieved
        # chunk is citable by its own reference; a chunk the search did not
        # return is not, which is what stops a fabricated citation.
        sources = {f"{attempt['assignment_id']}#response": attempt["submission"]}
        if chunks:
            sources.update({c.cite(): c.text for c in chunks})
        else:
            sources["course_notes"] = notes
        items = provenance.check_evidence(result.items, sources)
        bad = provenance.unsupported(items)

        ctx.append("evidence", {
            "items": [i.model_dump() for i in items],
            "uncertainty_notes": result.uncertainty_notes,
            "unsupported_count": len(bad),
        }, produced_by="agent:extract")
        return RunState.COMPARING

    def handle_comparing(ctx) -> RunState:
        """Relate this evidence to the student's earlier records.

        Kept apart from drafting so that "similar", "recurring", "improving" and
        "not enough evidence" is a record the checker can test, rather than a
        word buried inside a finding.

        Two transports, one contract. When TYPSAFE_JEV_MODEL is set, the
        verdict comes from the decisions model (jev_compare.judge) - a typed
        answer with a probability distribution and a confidence score. Below
        the confidence floor the verdict is not trusted and the run asks the
        professor instead, whatever the label says. Anything Jev-side that
        fails (network, unknown label, quota) falls back to the chat path -
        the fallback is the same SchemaFailure family the runner already
        handles, so a Jev outage degrades to the known-good transport rather
        than failing the run.
        """
        attempt = ctx.latest("attempt")
        prior = history.prior_records(ctx.store, attempt["student_id"], ctx.run_id)
        evidence_now = ctx.latest("evidence")

        comparison = None
        if jev.jev_available(ctx.settings):
            try:
                verdict = jev.judge(
                    settings=ctx.settings, budget=ctx.budget,
                    evidence=evidence_now, prior=prior, attempt=attempt,
                    week_gap=jev.compute_week_gap(
                        [r.get("date") for r in prior["evidence"]],
                        attempt.get("date", "")),
                )
                comparison = Comparison(
                    label=verdict.label,
                    related_refs=verdict.related_refs,
                    explanation=verdict.explanation,
                )
                # The confidence number is the reason Jev was wired here. A
                # low-confidence verdict on a consequential claim should be
                # read by a person, not trusted silently.
                if (verdict.label == "recurring"
                        and verdict.confidence < ctx.settings.jev_confidence_floor):
                    return _ask_professor(
                        ctx,
                        f"Jev judged this `{verdict.label}` but confidence "
                        f"{verdict.confidence:.2f} is below the "
                        f"{ctx.settings.jev_confidence_floor:.2f} floor.")
                ctx.append("jev_verdict", {
                    "label": verdict.label,
                    "confidence": verdict.confidence,
                    "probabilities": verdict.probabilities,
                    "model": ctx.settings.jev_model,
                }, produced_by="agent:jev")
            except (ModelError, Exception) as e:
                # Fall back, visibly: the failure is a record, not silent.
                ctx.append("failure", {
                    "kind": "jev_unavailable",
                    "detail": f"{type(e).__name__}: {e}",
                    "note": "fell back to the chat compare path",
                }, produced_by="agent:compare")

        if comparison is None:
            comparison = timed("compare", lambda: call(
                settings=ctx.settings, budget=ctx.budget,
                messages=build_compare_messages(evidence_now, prior,
                                                attempt["learning_objectives"]),
                schema=Comparison, step="compare",
            ), lambda r: r.label)

        # The model may not award `recurring` on a single assignment, whatever
        # it thinks it sees. Recurrence is a claim about more than one piece of
        # work, and that is a rule, so it lives in code.
        assignments = {p.get("assignment_id") for p in prior["evidence"]}
        assignments.discard(None)
        if comparison.label == "recurring" and len(assignments) + 1 < RECURRENCE_NEEDS_ATTEMPTS:
            comparison = comparison.model_copy(update={
                "label": "not_enough_evidence",
                "explanation": ("Downgraded in code: recurrence needs evidence from at "
                                f"least {RECURRENCE_NEEDS_ATTEMPTS} assignments. "
                                + comparison.explanation),
            })

        ctx.append("comparison", comparison.model_dump(), produced_by="agent:compare")
        return RunState.DRAFT_FINDING

    def handle_draft_finding(ctx) -> RunState:
        """Write a bounded finding, addressing the last rejection if there was one."""
        checks = ctx.history("check")
        rejected = None
        if checks and checks[-1].payload["verdict"] == "rejected":
            findings = ctx.history("finding")
            rejected = {
                "finding": findings[-1].payload if findings else None,
                "failed_check": checks[-1].payload["failed_check"],
                "detail": checks[-1].payload.get("detail", ""),
            }

        finding = timed("finding", lambda: call(
            settings=ctx.settings, budget=ctx.budget,
            messages=build_finding_messages(ctx.latest("evidence"),
                                            ctx.latest("comparison"),
                                            ctx.latest("attempt"), rejected),
            schema=Finding, step="finding",
        ), lambda r: f"revision {len(ctx.history('finding')) + 1}, {r.status}")
        # The revision number is ours to assign, not the model's to claim.
        revision = len(ctx.history("finding")) + 1
        ctx.append("finding", finding.model_copy(update={"revision": revision}).model_dump(),
                   produced_by="agent:finding")
        return RunState.EVIDENCE_CHECK

    def handle_evidence_check(ctx) -> RunState:
        """Accept, reject, or flag for review. The back-edge lives here."""
        finding = ctx.latest("finding")
        evidence = ctx.latest("evidence")
        comparison = ctx.latest("comparison")

        # Citation first, in code, asking no model. A finding may only rest on
        # evidence rows that survived the check - in THIS run, or in an earlier
        # run for the same student.
        #
        # The earlier runs matter. A recurring finding cites the assignment it
        # is recurring from, and that reference is legitimate precisely because
        # it is not in this run's evidence. Checking against this run alone
        # rejects every genuine cross-encounter claim, which is the one kind of
        # finding this system exists to make.
        attempt = ctx.latest("attempt")
        prior = history.prior_records(ctx.store, attempt["student_id"], ctx.run_id)
        supported_refs = {i["source_ref"] for i in evidence["items"] if i["supported"]}
        for row in prior["evidence"]:
            for item in row.get("items", []):
                if item.get("supported"):
                    supported_refs.add(item["source_ref"])

        fabricated = [r for r in finding["supporting_refs"] if r not in supported_refs]
        if fabricated:
            check = Check(verdict="rejected", failed_check="citation",
                          detail="Cites sources with no supported evidence row: "
                                 + ", ".join(fabricated))
        else:
            check = timed("check", lambda: call(
                settings=ctx.settings, budget=ctx.budget,
                messages=build_check_messages(finding, evidence, comparison),
                schema=Check, step="check",
            ), lambda r: r.verdict + (f" ({r.failed_check})" if r.failed_check else ""))

        ctx.append("check", check.model_dump(), produced_by="checker")

        if check.verdict == "accepted":
            return RunState.RECORD_UPDATED
        if check.verdict == "needs_review":
            return _ask_professor(ctx, "The finding was flagged as consequential.")

        # Rejected. Counted from the record history, never from budget.attempt.
        if len(ctx.history("finding")) >= MAX_FINDINGS:
            return _ask_professor(
                ctx, f"Drafted {MAX_FINDINGS} findings without one passing the check.")

        # Where it goes back to depends on why it failed.
        if check.failed_check == "citation":
            return RunState.EXTRACTING
        return RunState.COMPARING

    def handle_needs_review(ctx) -> RunState:
        """Suspended. The runner returns before reaching this; it exists so the
        state has a handler if a run is advanced while still waiting."""
        return RunState.NEEDS_REVIEW

    def handle_record_updated(ctx) -> RunState:
        """Close the record for this learning goal, setting the final status
        from the professor's review if there was one."""
        finding = dict(ctx.latest("finding"))
        comparison = ctx.latest("comparison")

        # Only write a review if a professor was actually asked. A run the
        # checker accepted never needed one, and recording `no_reply` for it
        # would make "nobody was asked" indistinguishable from "we asked and
        # were ignored" - which is the distinction the summary exists to show.
        if ctx.history("question"):
            answers = ctx.history("expert_answer")
            raw = answers[-1].payload.get("answer") if answers else None
            # The human boundary. Prose is classified into a typed record, and
            # only the typed record is allowed to affect the run. An answer
            # nothing reads means the professor was consulted and then ignored.
            decision = _classify_answer(raw)
            review = Review(decision=decision,
                            instructional_note=raw if decision != "no_reply" else None)
            ctx.append("review", review.model_dump(), produced_by="professor")

            if review.decision == "confirm" and comparison["label"] == "recurring":
                finding["status"] = "confirmed_recurring"
            elif review.decision == "reject":
                finding["status"] = "first_signal"

        ctx.append("finding", finding, produced_by="update")
        return RunState.RECOMMENDATION_READY

    def handle_recommendation_ready(ctx) -> RunState:
        """The professor-facing summary: what is here, what came before, what
        changed, what is uncertain, what they must decide."""
        attempt = ctx.latest("attempt")
        finding = ctx.latest("finding")
        comparison = ctx.latest("comparison")
        evidence = ctx.latest("evidence")
        reviews = ctx.history("review")
        asked = bool(ctx.history("question"))
        asked_no_reply = asked and bool(reviews) and reviews[-1].payload["decision"] == "no_reply"
        ctx.append("summary", {
            "student_id": attempt["student_id"],
            "assignment_id": attempt["assignment_id"],
            "status": finding["status"],
            "statement": finding["statement"],
            "comparison": comparison["label"],
            "related": comparison["related_refs"],
            "uncertainty": finding["uncertainty"],
            "next_step": finding["proposed_next_step"] if not asked_no_reply else None,
            "unsupported_evidence": evidence.get("unsupported_count", 0),
            # Three distinct outcomes, not two. "We asked and nobody replied"
            # must be a different artifact from one that quietly proceeded, AND
            # from one that never needed to ask.
            "professor": ("no_reply" if asked_no_reply
                          else reviews[-1].payload["decision"] if reviews
                          else "not_asked"),
            "professor_asked_no_reply": asked_no_reply,
        }, produced_by="recommend")
        return RunState.COMPLETE

    # ---------------------------------------------------------------- helpers

    def _ask_professor(ctx, why: str) -> RunState:
        finding = ctx.latest("finding")
        comparison = ctx.latest("comparison")
        callback.ask(
            ctx.store, ctx.run_id,
            question=(
                f"{why}\n\n"
                f"Finding: {finding['statement']}\n"
                f"Comparison: {comparison['label']} - {comparison['explanation']}\n\n"
                "Confirm, revise, reject, or request more evidence."
            ),
            context={"resume_state": RunState.RECORD_UPDATED.value,
                     "finding": finding, "comparison": comparison},
            settings=ctx.settings,
        )
        # callback.ask sets AWAITING_EXPERT; we want our own waiting state so
        # the professor's queue is legible in `get_state`.
        ctx.store.set_state(ctx.run_id, RunState.NEEDS_REVIEW)
        return RunState.NEEDS_REVIEW

    return SimpleNamespace(
        name="recall",
        handlers={
            RunState.NEW_ATTEMPT:          handle_new_attempt,
            RunState.EXTRACTING:           handle_extracting,
            RunState.COMPARING:            handle_comparing,
            RunState.DRAFT_FINDING:        handle_draft_finding,
            RunState.EVIDENCE_CHECK:       handle_evidence_check,
            RunState.NEEDS_REVIEW:         handle_needs_review,
            RunState.RECORD_UPDATED:       handle_record_updated,
            RunState.RECOMMENDATION_READY: handle_recommendation_ready,
        },
    )


def _retrieve_notes(ctx, attempt: dict, k: int = 3) -> list:
    """The course passages that bear on this submission.

    The query is the assignment prompt plus the student's own words, because
    what matters is the material relevant to *what they wrote*, not to the topic
    in general.

    Returns [] if no corpus has been ingested, if the extension will not load,
    or if anything else goes wrong - retrieval is an optimisation here, and a
    run that cannot retrieve should fall back to the full notes rather than
    fail. The failure is recorded so it is visible in a replay.
    """
    try:
        from slice import retrieve
        query = f"{attempt['assignment_prompt']} {attempt['submission']}"
        return retrieve.search(ctx.store, query, k=k)
    except Exception as e:
        ctx.append("failure", {"kind": "retrieval_unavailable",
                               "detail": f"{type(e).__name__}: {e}",
                               "note": "fell back to sending the whole notes"},
                   produced_by="extract")
        return []


def _classify_answer(raw: str | None) -> str:
    """Turn the professor's prose into a typed decision.

    Free text sitting in the history is a note. If nothing converts it, the
    professor was consulted and then ignored.
    """
    if not raw or not raw.strip():
        return "no_reply"
    text = raw.strip().lower()
    for word, decision in (("confirm", "confirm"), ("reject", "reject"),
                           ("revise", "revise"), ("more evidence", "request_more_evidence")):
        if word in text:
            return decision
    return "revise"
