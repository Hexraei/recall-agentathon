"""The report checker's second engine: Jev.

Why Jev was a better fit here than in compare
---------------------------------------------
The report check, after the teammates' own refactors, has been reduced to ONE
remaining judgement. The arithmetic left it one by one:

    concepts exist         -> check_citations()     (code)
    every verdict          -> enforce_verdicts()    (code, verdict_for())
    cross-topic pattern    -> enforce_pattern()     (code)
    when a concept is weak -> verdict_for()         (code, unit-tested)

What the check's prompt (prompts/report_check.md) tells the model to reject on
is three things - (1) a statement the counts contradict, (2) a claim about
something not measured, (3) language about the person. (1) is now answered in
code upstream; what survives to the model's call is (2) and (3) - "does this
sentence overreach the measurements, or describe the person instead of the
work?".

That is precisely a calibrated yes/no: one question, bounded bundle, a
consequential yes/no where a wrong "accept" ships a false sentence to a
student. Jev's `noul` question returns a probability and a confidence, and
CONFIDENCE BELOW THE FLOOR means the report is not silently accepted on a
coin toss it cannot articulate - it gets sent back with the software's own
explanation, or, on a repeated miss, flagged `_unverified` for the teacher.
Same architectural rule as the compare step: Jev judges; the loop, schema and
back-edge belong to the report pipeline, unchanged.

Fails the same way compare does: any Jev-side error silently (well, in the
trail) falls back to the chat checker, which remains the default path and
remains what runs when TYPSAFE_JEV_MODEL is unset.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from slice.config import Settings
from slice.llm import _Span

from .jev_compare import DECISIONS_API, JevError, TRANSPORT_ERRORS


class JevVerdict:
    """The typed answer for one report-under-review.

    `noul` in [0,1]: the probability the report is FALSE somewhere. Low noul
    = accept. High noul = reject. Confidence is Jev's own estimate of that
    answer; below `floor` the verdict is not trusted either way.
    """

    def __init__(self, noul: float, confidence: float, model: str):
        self.noul = noul
        self.confidence = confidence
        self.model = model
        self.detail = ""
        self.accepted = noul < 0.5
        self.failed_check = None if self.accepted else "claim_strength"


def _report_bullets(report: dict) -> list[str]:
    """One line per claim the report makes, numbered and named.

    The counts are the evidence bundle; the report's claims are the questions.
    Every claim the writer can make has a number sitting next to it, so the
    question is never "does this report seem right" (which is a mood) but
    "is claim 3 contradicted by the counts?" (a decision).
    """
    lines: list[str] = []
    for field in ("headline", "cross_topic_pattern", "next_step", "uncertainty"):
        v = report.get(field)
        if v:
            lines.append(f"[{field}] {v}")
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            lines.append(
                f"[{field}] concept={row.get('concept')} "
                f"verdict={row.get('verdict')} "
                f"evidence: \"{row.get('evidence')}\"")
    return lines


def build_jev_check_state(report: dict, facts: dict, kind: str) -> str:
    """The state Jev evaluates. Two sections: what was claimed, what was measured.

    The counts here are the same `facts` the chat checker sees (already
    enriched by `_with_wrong_answers` - wrong_answer_count, missed_in_topics,
    verdict-to-beat all in the rows). Nothing is asked that is derivable
    elsewhere.
    """
    measured = {
        k: facts[k] for k in ("score", "by_topic", "by_concept",
                              "students", "most_common_wrong_answers")
        if k in facts
    }
    return (
        f"REPORT KIND: {kind}\n\n"
        "CLAIMS THE REPORT MAKES (numbered for reference):\n"
        + "\n".join(f"  {i+1}. {b}" for i, b in enumerate(_report_bullets(report)))
        + "\n\nMEASURED COUNTS (computed in SQL, treat as fact):\n"
        + json.dumps(measured, indent=2)
    )


def _questions() -> dict:
    """Two typed questions. One does the work; the second exists so a rejection
    can name WHICH claim was false, which is what the redrafting prompt needs.
    """
    return {
        "false_somewhere": {
            "type": "noul",
            "instructions": (
                "Does this report contain at least one sentence that is FALSE "
                "about the measured counts, or a claim about something the "
                "counts cannot measure (rank against peers, effort, motive, "
                "future performance), or language about the person rather "
                "than the work? Style, tone, brevity and completeness are "
                "never reasons to say yes - only a false, unmeasurable, or "
                "ad-hominem claim is."),
            "criteria": {
                "true": ("At least one numbered claim is contradicted by the "
                          "counts, is not measurable from them, or is about "
                          "the person rather than the work."),
                "false": ("Every claim is consistent with the counts, "
                           "measurable, and about the work."),
            },
        },
        "bad_claim": {
            "type": "noul",
            "instructions": (
                "Quote the ONE claim number that is the clearest violation. "
                "If the first question was answered false (report is fine), "
                "this must be 0."),
            "criteria": {
                "true": "One specific numbered claim above is the violation.",
                "false": "No claim is a violation.",
            },
        },
    }


def judge(*, settings: Settings, budget, report: dict, facts: dict,
          kind: str, timeout: float = 60.0,
          json_blob: str | None = None) -> tuple[Any, dict]:
    """Check one report with Jev. Returns (ReportCheck-shaped verdict, meta).

    Mirrors check_citations()'s contract: the caller cannot tell, from the
    returned verdict's shape, which engine produced it.

    Raises JevError on any Jev-side failure. The caller (report._generate)
    catches, records, and falls back to the chat checker.

    `json_blob` is the test escape hatch, mirroring jev_compare.judge: pass
    pre-captured JSON to avoid the network. None in production.
    """
    budget.check_tokens()
    body = {
        "model": settings.jev_model,
        "state": build_jev_check_state(report, facts, kind),
        "questions": _questions(),
    }
    if json_blob is not None:
        data = json.loads(json_blob)
    else:
        try:
            r = httpx.post(DECISIONS_API,
                           headers={"Authorization": f"Bearer {settings.api_key}"},
                           json=body, timeout=timeout)
        except TRANSPORT_ERRORS as e:
            # Transport-level failure (network/timeout/malformed header like an
            # empty Bearer key): wrapped as JevError so the caller's outage path
            # treats it as an outage, not a crash.
            raise JevError(f"Jev transport failure: {type(e).__name__}: {e}") from e
        if r.status_code != 200:
            raise JevError(f"Jev HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
    budget.record_tokens((data.get("usage") or {}).get("total_tokens", 0))

    answers = data.get("answers", {})
    # noul answers carry no confidence field - the calibration IS the
    # probability. Treat Jev's own `confidence` as the distance from 0.5
    # (a coin flip is certainty of nothing): |2*(noul-0.5)|.
    noul = float((answers.get("false_somewhere") or {}).get("noul", 0.0))
    claim_q = (answers.get("bad_claim") or {})
    bad_noul = float(claim_q.get("noul", 0.0))
    reported_conf = (answers.get("false_somewhere") or {}).get("confidence")
    confidence = (float(reported_conf) if reported_conf is not None
                  else abs(noul - 0.5) * 2.0)
    model_served = data.get("model", settings.jev_model)

    v = JevVerdict(noul=noul, confidence=confidence, model=model_served)

    # The second question's whole job: name WHICH numbered claim is the
    # violation, so the redrafting prompt receives something actionable
    # instead of a generic objection. The numbered bullets live in the state
    # block (build_jev_check_state), so the number maps back to the sentence.
    claim_no = 0
    if not v.accepted:
        try:
            claim_no = int(float(claim_q.get("claim", 0) or 0))
        except (TypeError, ValueError):
            claim_no = 0
        claims = _report_bullets(report)
        if 0 < claim_no <= len(claims):
            v.detail = f"Jev names claim {claim_no}: {claims[claim_no - 1]}"
        else:
            v.detail = ("Jev judged the report false somewhere but did not "
                        "name a specific claim.")

    meta = {"noul_false": noul, "bad_claim_noul": bad_noul,
            "confidence": confidence, "model": model_served,
            "bad_claim": claim_no,
            "below_floor": confidence < settings.jev_confidence_floor}
    return v, meta
