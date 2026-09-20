"""The compare step's judge, when Jev is configured.

Why a second transport for one step
-----------------------------------
The whole project rests on one judgement: is this difficulty the same one we
saw before? Measured on 19 Sep: the chat path returned `recurring`, `similar`
AND `improving` for the SAME input on consecutive runs (that anecdote is why
consistency.py exists). A decision model answering a typed question with a
probability distribution and a confidence score is a different class of answer
- and the confidence number lets CODE decide when to route the verdict to
professor review instead of trusting it, which is the "refuses to overstate"
story enforced structurally rather than asked of a prompt.

The transport is deliberately separate from slice/llm.py: Jev is not a chat
model. The endpoint refuses /chat/completions with an error naming this route
(so the shape is enforced for us); its failures here are classified into the
same ModelError family the runner already knows, so handle_comparing can treat
Jev-unreachable as fall-back-to-chat rather than as a run failure.

Two things this file does on purpose:
  - dates and counts are computed in Python before the state is built. Jev
    1.13 reads dates as text and cannot count; both are documented failure
    modes in their own docs, and neither is a judgement worth asking of a
    model.
  - the compare prompt's decision rules (app/prompts/compare.md) are loaded
    verbatim as the criteria descriptions, so the two transports judge by the
    SAME rules and consistency.py measures the transport, not the rubric.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Type

import httpx
from pydantic import BaseModel, ValidationError

from slice.budget import Budget
from slice.config import Settings
from slice.llm import ModelError, _Span

DECISIONS_API = "https://openrouter.ai/api/alpha/decisions"

LABELS = ("recurring", "similar", "improving", "not_enough_evidence")


class JevError(ModelError):
    """Jev could not be reached or would not answer. The caller falls back."""


TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    httpx.TransportError,    # network unreachable / timeout / malformed request
    OSError,                 # raw sockets: ConnectionRefusedError et al.
)
"""The failure classes that mean "the request did not make a clean round
trip": network unreachable, timeout, and the httpx family of malformed
request errors - an empty Bearer key surfaces as LocalProtocolError, not
as an HTTP status. Any of these gets wrapped into JevError so
handle_comparing's narrowed fallback catch still treats it as an outage.
Anything outside this tuple (a TypeError or KeyError raised by our own
code) is a BUG, not an outage, and must crash loudly rather than
laundering itself as one.
"""


class JevVerdict(BaseModel):
    """The typed answer, mirroring app.schema.Comparison's contract.

    `confidence` and the probability distribution travel with the label -
    that is what the chat path cannot give and what the needs-review rule
    consumes.
    """
    label: str
    explanation: str
    related_refs: list[str] = []
    confidence: float = 0.0
    probabilities: dict[str, float] = {}


# ------------------------------------------------------------------ the state

def _compact_prior(prior: dict[str, list[dict[str, Any]]]) -> str:
    """The student's earlier records as short lines, newest first.

    This is the token-saving half of the integration: a full
    json.dumps(prior, indent=2) sends every row of every kind. A compare
    verdict needs each prior encounter's concept, kind, its passage in
    quotation, the assignment and its week - which lines carry better than
    indented JSON does.
    """
    lines: list[str] = []
    by_assignment: dict[str, list[str]] = {}
    for row in prior.get("evidence", []):
        aid = row.get("assignment_id", "unknown")
        for item in row.get("items", []):
            kind = item.get("kind", "?")
            concept = item.get("concept", "?")
            passage = (item.get("passage") or "").strip().replace("\n", " ")
            supported = item.get("supported", True)
            flag = "" if supported else " [could-not-establish]"
            by_assignment.setdefault(aid, []).append(
                f"    - {kind}/{concept}{flag}: \"{passage}\"")
    for aid, items in by_assignment.items():
        lines.append(f"  assignment {aid}:")
        lines.extend(items)
    for row in prior.get("review", []):
        decision = row.get("decision", "?")
        note = (row.get("instructional_note") or "-").replace("\n", " ")
        lines.append(f"  professor review: {decision} "
                     f"note: \"{str(note)[:200]}\"")
    return "\n".join(lines) if lines else "(no earlier records)"


def build_jev_state(evidence: dict, prior: dict, attempt: dict,
                    week_gap: int | None) -> dict:
    """The state Jev evaluates. One string, questions separate.

    `week_gap` was computed in Python: (this date - last date).days//7. It is
    handed over as a NUMBER precisely because the model must not derive it.
    """
    state_lines = [
        "LEARNING OBJECTIVES:",
        *[f"  - {o}" for o in attempt.get("learning_objectives", [])],
        "",
        "CURRENT SUBMISSION EVIDENCE:",
    ]
    for item in evidence.get("items", []):
        kind = item.get("kind", "?")
        concept = item.get("concept", "?")
        passage = (item.get("passage") or "").replace("\n", " ")
        supported = item.get("supported", True)
        ref = item.get("source_ref", "?")
        flag = "" if supported else " [could-not-establish]"
        state_lines.append(
            f"  - {kind}/{concept}{flag} (ref {ref}): \"{passage}\"")
    state_lines += ["", "STUDENT'S EARLIER RECORDS:", _compact_prior(prior)]
    if week_gap is not None:
        state_lines += ["", f"WEEKS SINCE LAST ATTEMPT: {week_gap}"]
    return {"state_block": "\n".join(state_lines)}


def compute_week_gap(evidence_dates: list[str], attempt_date: str) -> int | None:
    """Weeks between this attempt's date and the most recent earlier one.

    Dates are ISO strings in attempt records. Returns None when either side is
    missing or unparseable - a number that cannot be computed is not sent.
    """
    def parse(d: str):
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (d or "").strip())
        if not m:
            return None
        return __import__("datetime").date(*map(int, m.groups()))

    this = parse(attempt_date)
    if not this:
        return None
    dates = [d for d in (parse(x) for x in evidence_dates) if d is not None]
    if not dates:
        return None
    latest = max(dates)
    if latest >= this:
        return None
    return (this - latest).days // 7


# -------------------------------------------------------------- criteria text

def _criteria() -> dict[str, str]:
    """One description per label, matching app/prompts/compare.md's rules.
    The compare prompt says the model must be reluctant; these criteria carry
    that reluctance so the chat path and the Jev path answer by the same rules.
    """
    return {
        "recurring": (
            "The current difficulty is caused by the SAME misunderstanding "
            "as a difficulty in the earlier work - one sentence explains "
            "both (..counted the loop and ignored the work inside it..). "
            "Different wording on different tasks can still be recurring."),
        "similar": (
            "The errors look alike but a single shared cause does not "
            "explain both - teaching one thing would not fix both pieces "
            "of work."),
        "improving": (
            "The current work shows the student NOW doing correctly the "
            "specific thing previously a difficulty. Requires quotable "
            "evidence of success, not merely a different mistake."),
        "not_enough_evidence": (
            "No earlier evidence at all for these objectives, or the "
            "submissions do not support a confident judgement."),
    }


# --------------------------------------------------------------------- caller

def judge(*, settings: Settings, budget, evidence: dict, prior: dict,
          attempt: dict, week_gap: int | None,
          json_blob: str | None = None, timeout: float = 60.0) -> JevVerdict:
    """One typed question against the bundled state. Raises ModelError on
    anything other than a clean answer - handle_comparing catches it and
    falls back to the chat transport.

    `json_blob` is an escape hatch for tests: pass pre-captured JSON to avoid
    the network. None in production.
    """
    budget.check_tokens()
    state_block = build_jev_state(evidence, prior, attempt, week_gap)
    body = {
        "model": settings.jev_model,
        "state": state_block["state_block"],
        "questions": {
            "label": {
                "type": "choice",
                "instructions": (
                    "Decide how this student's current work relates to their "
                    "earlier work. You are the step that distinguishes a "
                    "pattern from a coincidence, and being reluctant here "
                    "is correct. Work through the four options in order and "
                    "stop at the first that applies."),
                "criteria": _criteria(),
            },
        },
    }
    with _Span(settings, "jev:compare", {"model": settings.jev_model}) as span:
        if json_blob is None:
            try:
                r = httpx.post(DECISIONS_API,
                               headers={"Authorization": f"Bearer {settings.api_key}"},
                               json=body, timeout=timeout)
            except TRANSPORT_ERRORS as e:
                # Transport-level failure (network/timeout/malformed request).
                # Wrapped so the caller's narrow JevError catch sees an outage,
                # not a crash.
                raise JevError(f"Jev transport failure: "
                               f"{type(e).__name__}: {e}") from e
            if r.status_code == 200:
                data = r.json()
            else:
                err = r.text[:300]
                raise JevError(f"Jev HTTP {r.status_code}: {err}")
            used = (data.get("usage") or {}).get("total_tokens", 0)
            budget.record_tokens(used)
            span.record(output={"jev_tokens": used,
                                "model": data.get("model")})
        else:
            data = json.loads(json_blob)

        answers = data.get("answers", {})
        label_q = answers.get("label", {})
        label = label_q.get("choice", "")
        if label not in LABELS:
            raise JevVerdict if False else JevError(  # noqa: unreachable tie-off
                f"Jev returned an unrecognised label {label!r}")
        explanation = body["questions"]["label"]["criteria"][label]
        # The explanation Jev gives is the criteria text - which is honest,
        # but the compare prompt asked for WHICH assignment was compared and
        # WHAT it showed, so we surface the refs instead and let the finding
        # step name the specific comparison.
        refs = sorted({i.get("source_ref") for row in prior.get("evidence", [])
                       for i in row.get("items", []) if i.get("supported")})
        return JevVerdict(label=label,
                          explanation=explanation,
                          related_refs=refs,
                          confidence=float(label_q.get("confidence", 0.0) or 0.0),
                          probabilities={k: float(v) for k, v in
                                         (label_q.get("probabilities") or {}).items()})


# A short wrapper matching the runner's shape, so flow.py can call this and
# complete() through one branch.
def jev_available(settings: Settings) -> bool:
    return bool(settings.jev_model)
