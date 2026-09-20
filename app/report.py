"""The two report agents: one per student, one per class.

Why the report is where the model runs, and the quiz is not
-----------------------------------------------------------
Running the full extract/compare/draft/check pipeline per ANSWER would mean 20
questions x 4 model calls = 80 calls per student, roughly two minutes of a
tester staring at a spinner, and an instant collision with Groq's 8000 tokens a
minute. It would also leak per-question feedback, which the design explicitly
rules out: a student who learns they got Q3 wrong answers Q4 differently, and
the twenty answers stop being twenty independent observations.

So the quiz writes rows. The agent runs once, at the end, over all twenty
together - which is also the only point at which the interesting question can
even be asked. "Did they miss this one" is a scoreboard. "Do these five misses
share one cause" needs all five in front of it at once.

The same back-edge as app/flow.py
---------------------------------
Both reports draft, then check, then either accept or route BACK with the reason:

    citation       -> DRAFTING   (cited a concept the student never answered on)
    claim_strength -> DRAFTING   (claimed a pattern the counts do not support)

The citation half is code, not a model - a report may only name concepts that
appear in the actual response rows. That is the same rule the finding checker
enforces in app/flow.py, applied to a different artifact.

The counts are computed in SQL (app/roster.py) and handed to the model as facts.
The model's job is to say what they MEAN, never to work out what they are.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from typing import Literal

from slice.llm import complete
from slice.records import RunState

from . import roster

_PROMPTS = Path(__file__).parent / "prompts"

MAX_DRAFTS = 2
"""Redraft budget for a report. Counted from drafts written, never shared with
the token/attempt fence in slice/budget.py - two malformed JSON replies must not
silently spend the revisions this counter exists to protect.

Lowered from 3 on measurement, and re-confirmed since.

The original reason no longer applies: it was that the checker rejecting draft
2 would reject draft 3 as well, on a different marginal objection. That checker
was a model, and those objections were mostly hallucinated - see
docs/evidence/bug-05-checker-hallucinated-contradictions.md. The checks are
code now and they do not invent objections, so the question had to be asked
again rather than inherited.

Re-measured over 96 report runs on the real cohort under the current checks:

    95 accepted the first draft
     1 was rejected, redrafted, and accepted
     0 spent the budget without a clean draft

So a second draft is occasionally needed and, when it is, always sufficient.
Two remains right for a different reason than it was chosen for: not "a third
draft would not help" but "a second one already finishes the job". It also
keeps the back-edge real - a rejection with a reason, and a rewrite that
answers it, which is the behaviour worth watching.
"""

DEADLINE_SECONDS = 90.0
"""Wall-clock fence on a whole report, checked between drafts.

A third counter, separate from MAX_DRAFTS and from the token budget, because it
fences a different failure. During a network drop on Day 1 one report sat for
2,370 seconds - roughly forty minutes - stacking per-request timeouts across a
primary, a fallback and their retries before finally raising. No individual
timeout was wrong; they simply composed. MAX_DRAFTS does not help here, because
the time is spent INSIDE a single draft's call chain, and the token budget does
not help either, because a request that never returns never records any tokens.

Nobody watches a blank page for forty minutes. Past this deadline the loop stops
redrafting and ships what it has, flagged - see `_unverified`.
"""


# ------------------------------------------------------------------- contracts

class ConceptCall(BaseModel):
    concept: str
    """Must match a concept the student actually answered on. Checked in code."""
    verdict: Literal["strong", "mixed", "weak"]
    evidence: str = Field(default="", max_length=160)
    """What THIS concept's wrong answers have in common, in one sentence - or
    empty when there are none.

    Optional since measuring the real cohort. `evidence` is a reading of the
    MISTAKES, so a concept with no mistakes leaves the model nothing to say and
    it fills the space instead: "You got all of these right" appeared 55 times
    across 150 entries, next to a score that already says exactly that. Worse,
    it is the same sentence every time, so 67% of reports repeated a line - and
    a student who reads the identical sentence under three different headings
    can see the report is not really looking at them.

    Empty is now the honest answer for a clean concept, and strip_empty_evidence()
    enforces it in code rather than asking the prompt nicely.

    Lowered from 300 after a genuinely all-strong report (5 concepts, all
    `strong`, nothing to trim) intermittently overran settings.max_tokens and
    was truncated mid-JSON - the same failure as bug 01, recurring because 5
    entries at 300 characters each, plus a headline and next_step, sometimes
    does not fit. A hard character cap holds regardless of how many concepts a
    student happens to have; prompt wording asking for brevity does not.
    """


# The length bounds below are not stylistic. A request is capped at
# settings.max_tokens (1200 by default), and a report that runs past it is
# truncated mid-JSON and fails to parse - which is exactly how the lowest-
# scoring student in the first full warm run failed, because they had the most
# to say about. Bounding the schema is the fix that holds regardless of how
# many gaps a student turns out to have, and a report this size is the one a
# student will actually read.

class StudentReport(BaseModel):
    headline: str = Field(max_length=200)
    """One sentence a student can read without a teacher present."""
    strengths: list[ConceptCall] = Field(default_factory=list, max_length=4)
    gaps: list[ConceptCall] = Field(default_factory=list, max_length=4)
    pattern_concept: str | None = None
    """Which concept `cross_topic_pattern` is about, copied from by_concept.

    Exists so the pattern's support is checkable in code: a concept spans two
    or more topics or it does not, and that is a fact already computed in
    `missed_in_topics`. Asked to judge it instead, the checker rejected the
    pattern on nearly every phrasing - including the planted 4-topic case that
    the whole system exists to find."""

    cross_topic_pattern: str | None = Field(default=None, max_length=600)
    """The point of the whole exercise: one cause showing up in several topics,
    or None when the misses genuinely do not share one."""
    next_step: str = Field(max_length=400)
    uncertainty: str = Field(max_length=600)
    """What this quiz cannot tell you. Twenty questions is a thin sample and the
    report has to say so rather than imply a diagnosis."""


class ClassReport(BaseModel):
    headline: str = Field(max_length=200)
    teach_again: list[ConceptCall] = Field(default_factory=list, max_length=4)
    """Concepts where the CLASS is weak - a teaching problem, not a tutoring one."""
    solid: list[ConceptCall] = Field(default_factory=list, max_length=3)
    split: str | None = Field(default=None, max_length=600)
    """Where the class divides rather than sharing one level - the case that
    changes what a teacher should do next."""
    next_step: str = Field(max_length=400)
    uncertainty: str = Field(max_length=600)


class ReportCheck(BaseModel):
    verdict: Literal["accepted", "rejected"]
    failed_check: Literal["citation", "claim_strength"] | None = None
    detail: str = ""


# -------------------------------------------------------------------- prompts

def _prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def _fenced(facts: dict, who: str) -> str:
    """The facts, clearly marked as INPUT and nothing else.

    Handed over as a bare JSON blob, the counts get echoed straight back: the
    model emitted `department` and `score` as top-level keys because the thing
    it was reading looked like the thing it was being asked to write, and the
    reply failed schema validation. A fence and an explicit field list fixed
    what no amount of instruction-wording did.
    """
    return (f"<counts>  ← INPUT. The measured counts for this {who}, computed "
            "in SQL. Read them, treat them as fact, and do NOT copy any of "
            "these keys into your reply.\n"
            + json.dumps(facts, indent=2)
            + "\n</counts>")


# Naming the keys is not enough - asked for "strengths, gaps", the model
# returned strengths as a list of plain strings and failed validation. The
# shape of the list items has to be spelled out too.
_ENTRY = '{"concept": str, "verdict": str, "evidence": str}'

_STUDENT_SHAPE = (
    '{"headline": str, '
    f'"strengths": [{_ENTRY}], "gaps": [{_ENTRY}], '
    '"pattern_concept": str|null, "cross_topic_pattern": str|null, '
    '"next_step": str, "uncertainty": str}')

_CLASS_SHAPE = (
    '{"headline": str, '
    f'"teach_again": [{_ENTRY}], "solid": [{_ENTRY}], '
    '"split": str|null, "next_step": str, "uncertainty": str}')


def build_student_messages(facts: dict, rejected: dict | None) -> list[dict]:
    user = [_fenced(facts, "student"),
            "Your reply is a JSON object of exactly this shape, with no extra "
            f"keys:\n{_STUDENT_SHAPE}\n\nEvery item in `strengths` and `gaps` "
            "is an object with all three fields - never a bare string."]
    if rejected:
        user.append(
            "Your previous report was REJECTED.\n"
            + json.dumps(rejected["report"], indent=2)
            + f"\n\nFailed check: {rejected['failed_check']}\nWhy: {rejected['detail']}"
            + "\n\nWrite a report that survives that objection. Do not restate "
              "the rejected claim in softer words."
        )
    return [{"role": "system", "content": _prompt("student_report")},
            {"role": "user", "content": "\n\n---\n\n".join(user)}]


def build_class_messages(facts: dict, rejected: dict | None) -> list[dict]:
    user = [_fenced(facts, "class"),
            "Your reply is a JSON object of exactly this shape, with no extra "
            f"keys:\n{_CLASS_SHAPE}\n\nEvery item in `teach_again` and `solid` "
            "is an object with all three fields - never a bare string."]
    if rejected:
        user.append(
            "Your previous report was REJECTED.\n"
            + json.dumps(rejected["report"], indent=2)
            + f"\n\nFailed check: {rejected['failed_check']}\nWhy: {rejected['detail']}"
            + "\n\nWrite a report that survives that objection."
        )
    return [{"role": "system", "content": _prompt("class_report")},
            {"role": "user", "content": "\n\n---\n\n".join(user)}]


# ----------------------------------------------------------------- the facts

def student_facts(store, student_id: str) -> dict[str, Any]:
    """Everything a student report is allowed to see: this student, and only
    this student.

    No class averages, no cohort context, no peer comparison of any kind. A
    student's diagnosis stands on their own work or it is not a diagnosis - and
    a report that says "below the class average" has told them where they rank,
    which is not what this system is for and is not something a multiple-choice
    quiz has earned the right to say.

    The class view is a separate artifact for a separate reader (class_facts,
    below). The two departments never meet at all: the questions differ, the
    concepts differ, and every query is scoped to one department.
    """
    stu = roster.student(store, student_id) or {}
    got, asked = roster.score(store, student_id)
    return {
        "department": stu.get("department", ""),
        "score": {"correct": got, "asked": asked},
        "by_topic": roster.by_topic(store, student_id),
        "by_concept": _with_wrong_answers(
            roster.by_concept(store, student_id),
            roster.misconceptions(store, student_id)),
    }


def _with_wrong_answers(concepts: list[dict], wrong: list[dict]) -> list[dict]:
    """Fold each concept's wrong answers into its own row, and stamp on the
    verdict the counts earn.

    The flat `wrong_answers` list is deliberately NOT passed through beside
    this. Handed both, the writer had to match them up itself - which concept
    owns which mistake, how many mistakes that is, how many topics they span -
    and it got that matching wrong in 13 of 15 rejections measured across a
    cohort: "claims two mistakes, the counts show one", "claims three topics,
    the wrong answers show two".

    That is bookkeeping, not judgement, and the same lesson as verdict_for():
    a model asked to do clerical work alongside reasoning will do the clerical
    work badly and then reason confidently from it. So every count it needs is
    computed here and sits in the row it belongs to. Nothing is left to match.
    """
    by_concept: dict[str, list[dict]] = {}
    for w in wrong:
        by_concept.setdefault(w["concept"], []).append(w)

    out = []
    for row in concepts:
        mine = by_concept.get(row["concept"], [])
        asked = row.get("asked", row.get("answered", 0))
        # `topics` is dropped because `missed_in_topics` below is the same list
        # under a second name. Two keys holding one fact is an invitation to
        # cite the one the prompt does not mention, and then to disagree with it.
        row = {k: v for k, v in row.items() if k != "topics"}
        out.append({
            **row,
            "verdict": verdict_for(row["correct"], asked),
            "wrong_answer_count": len(mine),
            "missed_in_topics": sorted({w["topic"] for w in mine}),
            "wrong_answers": [{"topic": w["topic"], "mistake": w["misconception"]}
                              for w in mine],
        })
    return out


def class_facts(store, department: str) -> dict[str, Any]:
    concepts = roster.class_by_concept(store, department)
    for row in concepts:
        row["verdict"] = verdict_for(row["correct"], row["asked"])
    return {
        "department": department,
        "students": roster.class_size(store, department),
        "by_topic": roster.class_by_topic(store, department),
        "by_concept": concepts,
        "hardest_questions": roster.class_by_question(store, department)[:8],
        "most_common_wrong_answers": roster.class_common_wrong(store, department),
    }


# ------------------------------------------------------------ citation, in code

def verdict_for(correct: int, asked: int) -> str:
    """The verdict a concept's counts earn. Arithmetic, in code.

    This was originally stated as a rule in both prompts and left to the model.
    It did not work. Measured across a full cohort, EVERY report hit the redraft
    ceiling, and reading the rejections showed both sides failing at the same
    thing: the writer assigned `weak` to a concept scoring 4 of 5, and the
    checker "corrected" 0-of-3 to `strong`. Two models disagreeing about
    division is not a judgement call to be tuned with better wording - it is a
    calculation, and a calculation belongs in code where it is right every time
    and can be unit-tested.

    What is left for the model is the part that actually needs judgement: which
    concepts are worth reporting, what the wrong answers have in common, and
    what to do about it.
    """
    if asked <= 2:
        return "mixed"          # too few to separate a gap from a slip
    # "All but one" is a student-scale rule - it means a single slip across a
    # handful of questions. Past a handful, `asked` is a whole class's answers
    # and one wrong out of thirty is not the same claim, so it goes
    # proportional there too.
    if correct == asked or (4 <= asked <= 8 and correct == asked - 1) \
            or correct >= asked * 0.8:
        return "strong"
    # Proportional, not a fixed count. "One or none correct" reads right for a
    # student answering 3-5 questions, and is nonsense for a class report where
    # `asked` is every answer from every student - 2 correct out of 30 is
    # plainly weak, and an absolute threshold called it `mixed`.
    if correct <= 1 or correct <= asked * 0.34:
        return "weak"
    return "mixed"


# Which list an entry belongs in, once its verdict is known. `gaps` and
# `teach_again` are the weak lists; `strengths` and `solid` the strong ones.
_WEAK_LIST = {"strengths": "gaps", "solid": "teach_again"}
_STRONG_LIST = {v: k for k, v in _WEAK_LIST.items()}


def enforce_verdicts(report: dict, facts: dict) -> list[str]:
    """Set every verdict from the counts, and move the entry to the list that
    verdict belongs in. Both, in place.

    The move is the half that is easy to forget, and forgetting it is worse
    than doing nothing: correcting a 4-of-5 concept to `strong` while leaving
    it under `gaps` produces a report that says "gap: strong", which is a
    contradiction the checker then rejects on every single draft. Measured:
    reports sat at the redraft ceiling until the entry moved lists too.

    A `mixed` entry stays where the model put it - mixed is legitimately
    reportable as either a soft strength or a soft gap, and that IS a judgement
    call, unlike the arithmetic.

    Returns the corrections made, for the record.
    """
    counts = {r["concept"]: r for r in facts.get("by_concept", [])}
    fixed: list[str] = []
    moves: list[tuple[str, str, dict]] = []

    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            row_counts = counts.get(row["concept"])
            if not row_counts:
                continue       # the citation gate handles invented concepts
            asked = row_counts.get("asked", row_counts.get("answered", 0))
            want = verdict_for(row_counts["correct"], asked)
            score = f"({row_counts['correct']} of {asked})"

            changed = row.get("verdict") != want
            was = row.get("verdict")
            row["verdict"] = want

            # A strong concept filed under gaps, or a weak one under strengths.
            dest = (_STRONG_LIST.get(field) if want == "strong"
                    else _WEAK_LIST.get(field) if want == "weak" else None)
            if dest:
                moves.append((field, dest, row))

            if changed or dest:
                note = f"{row['concept']}: "
                note += f"{was} -> {want} {score}" if changed else f"{want} {score}"
                if dest:
                    note += f", moved {field} -> {dest}"
                fixed.append(note)

    for src, dest, row in moves:
        report[src].remove(row)
        # Not if the destination already names this concept. A writer may list
        # a concept under `gaps` AND `strengths` - measured on the real cohort:
        # one draft had four strengths and two gaps, all six concepts distinct
        # within their own list, but both gaps duplicating a concept already in
        # strengths. Moving them on verdict then produced a `strengths` list
        # naming two concepts twice, each with the same sentence, which is what
        # a student actually saw. The move is right; appending blindly is not.
        if any(x["concept"] == row["concept"] for x in report.get(dest) or []):
            fixed.append(f"{row['concept']}: dropped duplicate entry from {src}")
            continue
        report.setdefault(dest, []).append(row)

    return fixed


def _cited(report: dict) -> list[str]:
    out = []
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            out.append(row["concept"])
    return out


def enforce_pattern(report: dict, facts: dict) -> str | None:
    """Drop a cross-topic pattern the counts do not support. In code.

    Support is a fact, not a judgement: the named concept's wrong answers span
    two or more topics, or they do not, and `missed_in_topics` already says
    which. Left to the checker, this was rejected on nearly every phrasing -
    including the planted case spanning four topics - which pinned reports at
    the redraft ceiling over the one field the report exists for.

    An unsupported pattern is REMOVED rather than sent back. There is nothing
    for a rewrite to fix: if no concept spans two topics, no wording makes one
    appear, and three more drafts will not change that.

    Returns a note for the trail, or None when nothing was dropped.
    """
    claim = report.get("cross_topic_pattern")
    if not claim:
        return None

    spans = {r["concept"]: r.get("missed_in_topics", [])
             for r in facts.get("by_concept", [])}
    named = report.get("pattern_concept")

    # Fall back to whichever named concept actually appears in the prose, so a
    # writer that skipped the field is not punished for a real pattern.
    if named not in spans:
        named = next((c for c in spans if c.lower() in claim.lower()), None)

    if named is None:
        report["cross_topic_pattern"] = None
        report["pattern_concept"] = None
        return "dropped pattern: names no concept from the counts"

    if len(spans[named]) < 2:
        report["cross_topic_pattern"] = None
        report["pattern_concept"] = None
        return (f"dropped pattern: '{named}' has wrong answers in "
                f"{len(spans[named])} topic(s), not two or more")

    report["pattern_concept"] = named
    return None


# ------------------------------------------------ evidence, in code

def strip_empty_evidence(report: dict, facts: dict) -> list[str]:
    """Clear `evidence` on any concept with nothing to explain. In place.

    `evidence` says what the WRONG ANSWERS have in common. A concept with none
    has no such sentence to write, and asked for one anyway the model writes
    filler: "You got all of these right", 55 times in 150 entries on the real
    cohort, beside a score already showing 3/3.

    Removed rather than sent back, on the same reasoning as enforce_pattern():
    there is nothing for a rewrite to fix. No wording turns an absent mistake
    into an observation about one, and the score already carries the fact.

    Returns notes for the trail.
    """
    counts = {r["concept"]: r for r in facts.get("by_concept", [])}
    cleared: list[str] = []
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            if not (row.get("evidence") or "").strip():
                continue
            row_counts = counts.get(row["concept"])
            if not row_counts:
                continue           # the citation gate handles invented concepts
            if row_counts.get("wrong_answer_count", 0) == 0:
                row["evidence"] = ""
                cleared.append(f"{row['concept']}: cleared evidence (no wrong answers)")
    return cleared


def check_distinct_evidence(report: dict, facts: dict) -> ReportCheck | None:
    """One sentence may not stand in for two different concepts.

    Measured on the real cohort: one sentence was reused across different
    concepts 36 times in 30 reports - most often a generic line, but sometimes
    a specific reading of one concept's mistakes pasted onto another's, which
    says something false about the second. A student reading the same sentence
    under three headings can see the report is not looking at them separately.

    Unlike the filler case this IS sent back: the mistakes are there to be
    described, the model simply described them once and reused it, and that is
    something a rewrite can fix.
    """
    # A concept may appear once in the whole report. Listing it twice - even
    # with the same verdict and the same sentence - is a duplicate entry a
    # student sees as the report stuttering. enforce_verdicts() no longer
    # creates these, but a draft can still arrive with one.
    everywhere: dict[str, str] = {}
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            first = everywhere.get(row["concept"])
            if first is not None:
                return ReportCheck(
                    verdict="rejected", failed_check="claim_strength",
                    detail=(f"'{row['concept']}' is listed twice (in {first} "
                            f"and {field}). Name each concept once."))
            everywhere[row["concept"]] = field

    seen: dict[str, str] = {}
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            text = (row.get("evidence") or "").strip()
            if not text:
                continue
            first = seen.get(text.lower())
            if first is not None and first != row["concept"]:
                return ReportCheck(
                    verdict="rejected", failed_check="claim_strength",
                    detail=(f"The sentence '{text}' is used for both "
                            f"'{first}' and '{row['concept']}'. Each entry must "
                            "describe its own concept's mistakes; write a "
                            "different sentence for each, or leave one empty."))
            seen.setdefault(text.lower(), row["concept"])
    return None


def check_citations(report: dict, facts: dict) -> ReportCheck | None:
    """Code-side citation gate. Returns a rejection, or None to continue.

    A report may only name concepts that appear in the measured counts. This
    asks no model, which is the point: a model asked whether its own citation is
    real will tell you yes.
    """
    real = {r["concept"] for r in facts.get("by_concept", [])}
    invented = sorted({c for c in _cited(report) if c not in real})
    if invented:
        return ReportCheck(
            verdict="rejected", failed_check="citation",
            detail="Names concepts with no answered questions behind them: "
                   + ", ".join(invented))
    return None


# ---------------------------------------------------------- claim_strength, in code

# A checker model was asked to find a sentence the counts contradict. Measured
# across a real cohort (10 students, both departments), every rejection pulled
# from demo.db was the checker inventing a contradiction that was not there:
#
#   "the counts show 3 correct out of 3 asked" used to reject a sentence
#   saying all three were right - the TRUE case, rejected as false, twice.
#
#   "8 of 20" rejected against a headline that also says "8 of 20", verbatim,
#   twice.
#
#   "one topic was clean" rejected by restating the fact that supports it.
#
# This is not a wording problem in report_check.md - three rounds of tightening
# that prompt changed which false rejections happened, not whether they did.
# It is the same capability gap `verdict_for()`, `enforce_pattern()` and
# `check_citations()` were all created to route around: a model asked to do
# arithmetic or exact structural comparison does it unreliably, even when the
# numbers are handed to it directly. Every one of those moves held up under
# measurement; every model-judged version of this exact task kept failing. So
# `claim_strength` moves the same way - the checker call is gone, not just its
# prompt.
#
# What is actually being verified is narrow: a report may not claim a clean
# sweep ("all", "every", "each", "always") on a concept that has any wrong
# answers, may not misquote the topic's or the student's own score, and may
# not compare the student/class to anyone else or describe their character.
# All three are exact, mechanical checks - the same kind of fact `verdict_for`
# already turns into a number instead of an opinion.

# A clean-sweep claim is a phrase asserting that EVERY answer on a concept was
# correct. The bar for adding one here is that it cannot appear in ordinary
# explanatory prose, because `evidence` describes the misconception as well as
# the score.
#
# Measured, and the reason this list is not merely "words like every and all":
# a first cut matched the bare substrings "every time" and "was right", and
# rejected
#
#   "The one miss assumed every append reallocates; amortised growth means
#    copies happen rarely, not every time."
#
# on a 4-of-5 concept - a sentence that explicitly ADMITS the miss, failed on a
# phrase describing the misconception rather than the student. That is the same
# false rejection the checker model was making, reproduced in code, which is
# worth more than the rule it was enforcing.
_SWEEP_PHRASES = (
    "all of these right", "all of them right", "all of these correct",
    "every answer here was right", "every answer here was correct",
    "every one of these", "each of these was right", "got them all right",
    "got it all right", "clean sweep", "nothing wrong here",
    "no mistakes here", "all correct", "every single one",
)

# "right every time", "right answer every time", "correct each time" - one
# family, too many wordings to list, so it gets a pattern instead.
_SWEEP_RE = re.compile(r"\b(right|correct)\b[^.]{0,20}\b(every|each)\s+time\b")

# A sentence that names a miss is not claiming a sweep, whatever else it says.
# This is what lets `evidence` describe the mistake in the same breath as the
# strength - "mostly solid; the one miss chose a sorted structure" - which the
# writer prompt explicitly asks for.
_ADMITS_A_MISS = (
    "one miss", "the miss", "the misses", "missed", "one wrong", "got wrong",
    "except", "apart from", "other than", "slipped", "one slip", "mostly",
)

# Ranking a STUDENT against the cohort. Multi-word phrases only - a bare
# "rank" matched "rank-deficient" in a robotics report about Jacobian
# singularities and rejected a correct sentence, which is the same class of
# false positive this check was built to remove. Anything short enough to sit
# inside a technical term does not belong in this list.
_COMPARISON_PHRASES = (
    "compared to", "compared with", "below average", "above average",
    "the class average", "than your peers", "than the rest", "than average",
    "in the top", "in the bottom", "percentile", "ranked against",
    "better than most", "worse than most",
)

# Only meaningful on a STUDENT report. A class report is about the cohort by
# definition, so "most students" is a description there, not a comparison.
_COHORT_PHRASES = ("most students", "other students", "the other students")

# "smart" is deliberately absent: it sits inside "smart pointer".
_CHARACTER_WORDS = (
    "lazy", "careless", "weak student", "strong student", "stupid",
    "not trying", "gave up", "does not care", "doesn't care",
    "not paying attention", "sloppy", "unmotivated",
)


def _claims_a_clean_sweep(text: str) -> bool:
    """Does this sentence assert that every answer on a concept was right?

    A sentence that names a miss does not, however it is otherwise phrased -
    see _ADMITS_A_MISS.
    """
    low = text.lower()
    if any(phrase in low for phrase in _ADMITS_A_MISS):
        return False
    return (any(phrase in low for phrase in _SWEEP_PHRASES)
            or _SWEEP_RE.search(low) is not None)


def _prose_fields(report: dict) -> list[tuple[str, str]]:
    """Every free-text field a report can make a claim in, labelled."""
    out = [("headline", report.get("headline") or "")]
    for field in ("strengths", "gaps", "teach_again", "solid"):
        for row in report.get(field) or []:
            out.append((f"{field}:{row.get('concept')}", row.get("evidence") or ""))
    if report.get("cross_topic_pattern"):
        out.append(("cross_topic_pattern", report["cross_topic_pattern"]))
    for field in ("next_step", "uncertainty", "split"):
        if report.get(field):
            out.append((field, report[field]))
    return out


def _headline_score_claim(headline: str) -> tuple[int, int] | None:
    """Pull an "X of Y" / "X out of Y" claim out of a headline, if it makes one.

    Only a small, deliberate grammar - the point is to catch a wrong number,
    not to parse arbitrary prose. A headline that does not use this shape makes
    no numeric claim this check can verify, and is left alone.
    """
    m = re.search(r"(\d+)\s*(?:of|out of)\s*(\d+)", headline)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def check_claim_strength(report: dict, facts: dict,
                        kind: str = "student") -> ReportCheck | None:
    """Code-side replacement for the model 'find a false sentence' check.

    Returns a rejection, or None to continue. See the note above this function
    for why this is code and not a model call.
    """
    overall = facts.get("score")  # student reports only
    # A class report is ABOUT the cohort, so cohort language is descriptive
    # there and only a ranking claim on a student report is a problem.
    comparisons = _COMPARISON_PHRASES
    if kind == "student":
        comparisons = comparisons + _COHORT_PHRASES
    concepts = {r["concept"]: r for r in facts.get("by_concept", [])}

    headline = report.get("headline") or ""
    claimed = _headline_score_claim(headline)
    if claimed and overall:
        got, asked = claimed
        if (got, asked) != (overall["correct"], overall["asked"]):
            return ReportCheck(
                verdict="rejected", failed_check="claim_strength",
                detail=(f"The headline says '{headline}' but the measured score "
                        f"is {overall['correct']} of {overall['asked']}."))

    for label, text in _prose_fields(report):
        if not text:
            continue
        if _claims_a_clean_sweep(text):
            # Which concept is this claim about, if any - a strengths/gaps/
            # teach_again/solid entry names one in its label.
            concept = label.split(":", 1)[1] if ":" in label else None
            row = concepts.get(concept) if concept else None
            if row is not None:
                asked = row.get("asked", row.get("answered", 0))
                if row["correct"] < asked:
                    return ReportCheck(
                        verdict="rejected", failed_check="claim_strength",
                        detail=(f"The sentence '{text}' claims a clean sweep for "
                                f"'{concept}', but the counts show "
                                f"{row['correct']} correct out of {asked} - "
                                "at least one wrong answer."))

        low = text.lower()
        hit = next((p for p in comparisons if p in low), None)
        if hit:
            return ReportCheck(
                verdict="rejected", failed_check="claim_strength",
                detail=f"The sentence '{text}' compares against other students "
                       f"('{hit}'), which this report is not given data for.")
        hit = next((p for p in _CHARACTER_WORDS if p in low), None)
        if hit:
            return ReportCheck(
                verdict="rejected", failed_check="claim_strength",
                detail=f"The sentence '{text}' describes the person rather than "
                       f"the work ('{hit}').")

    return None


# ------------------------------------------------------------------- the loop

def build_check_messages(report: dict, facts: dict, kind: str) -> list[dict]:
    """The chat checker's prompt, used when Jev is unset or Jev fails.

    Kept after main's mechanical-checker rewrite: check_citations and
    check_claim_strength (code) run first and catch the enumeratable lie
    classes; this transport covers what remains - phrasing a typed question
    about claim strength over the report body. The old system prompt is gone
    from main (bug-04 rewrote the check as code), so the ask carries its
    contract inline.
    """
    return [{"role": "system", "content": (
        "You check a report against the measured counts it must rest on. "
        "Answer accepted only if every claim is supported by the counts. "
        "If a claim is unsupported, verdict rejected with failed_check "
        "claim_strength and a detail naming the claim and the count it "
        "contradicts.")},
        {"role": "user", "content": (
            f"Report kind: {kind}\n\nReport under review:\n"
            + json.dumps(report, indent=2)
            + "\n\nThe measured counts it must rest on:\n"
            + json.dumps(facts, indent=2))}]


def _run_check(body: dict, facts: dict, kind: str, settings, budget,
               store, budget_run: str, trail: list, trace=None, call=None):
    """The check step, with two engines behind one contract.

    Jev (when TYPSAFE_JEV_MODEL is set) answers two typed questions - "is
    something here false/unmeasurable/ad-hominem?" and "which claim?" - and
    the answer is mapped onto the same ReportCheck the chat checker returns,
    so downstream code cannot tell which engine ran. Any Jev error (HTTP,
    quota, shape) falls back visibly: a trail record noting the fallback,
    then the chat checker as before. Jev unset (or settings absent, which is
    how the offline tests call the loop) = chat path untouched.

    A low-confidence verdict is treated the way compare treats one: not
    trusted, routed to a human. In the report loop that means the report
    ships flagged `_unverified` with a note in the trail rather than being
    silently accepted OR endlessly redrafted on a coin-flip.
    """
    if settings is None:
        # settings=None is the offline-test path. Main's mechanical checks
        # (citations, distinct-evidence, claim strength) have already answered
        # themselves in code by the time we get here with check=None - on
        # main, that means "accepted" with no transport at all. Match main:
        # skip any transport, accept, leave no debris.
        #
        # jev_model="" (Jev unset, settings PRESENT) is a different case - the
        # pre-Jev behaviour of this branch: the chat checker answers, so the
        # offline-by-config path keeps its transport.
        return ReportCheck(verdict="accepted")
    if not getattr(settings, "jev_model", ""):
        assert call is not None
        return call(settings=settings, budget=budget,
                    messages=build_check_messages(body, facts, kind),
                    schema=ReportCheck, step="report_check")
    from . import jev_report_check as jrc
    try:
        verdict, meta = jrc.judge(settings=settings, budget=budget,
                                  report=body, facts=facts, kind=kind)
    except Exception as e:
        trail.append({"step": "jev_fallback", "revision": None,
                      "body": {"detail": f"{type(e).__name__}: {str(e)[:200]}"}})
        assert call is not None
        return call(settings=settings, budget=budget,
                    messages=build_check_messages(body, facts, kind),
                    schema=ReportCheck, step="report_check")

    # The trail gets the calibration numbers, not just the outcome - the
    # same reason compare keeps a jev_verdict record.
    check = ReportCheck(verdict="accepted" if verdict.accepted else "rejected",
                        failed_check=verdict.failed_check,
                        detail=(f"jev noul={verdict.noul:.2f} "
                                f"confidence={verdict.confidence:.2f} "
                                f"(model {verdict.model})"
                                + (f" - {verdict.detail}" if verdict.detail else "")))
    if meta["below_floor"]:
        check = ReportCheck(
            verdict="accepted", failed_check=None,
            detail=check.detail + " BELOW CONFIDENCE FLOOR - unverified")
        body["_unverified"] = (
            f"Jev confidence {verdict.confidence:.2f} below "
            f"{settings.jev_confidence_floor:.2f}; report shipped unverified.")
    return check


def _generate(store, kind: str, key: str, facts: dict, schema, build, call,
              settings, budget_run: str, trace=None) -> tuple[dict, list[dict]]:
    """Draft -> check -> accept or go back. Returns (report, trail).

    `trail` is every draft and every check, in order. It is what gets shown on
    screen when a judge asks to see the agent actually revise something, and it
    is why the rejection detail is kept rather than collapsed into a retry.

    ONE Budget for the whole loop, built once. Rebuilding it per call would
    hand every request a fresh attempt counter, which is a fence that never
    closes - the exact failure the counters exist to prevent.
    """
    import time as _time
    from slice.budget import Budget
    budget = Budget(store, budget_run, settings)
    started = _time.time()

    trail: list[dict] = []
    rejected: dict | None = None
    body: dict = {}

    for attempt in range(1, MAX_DRAFTS + 1):
        # Checked BEFORE spending another draft, not after - the point is to
        # refuse to start work that will finish too late to be of use.
        if attempt > 1 and _time.time() - started > DEADLINE_SECONDS:
            body["_revisions"] = attempt - 1
            body["_unverified"] = (
                f"stopped after {_time.time()-started:.0f}s without a clean draft "
                f"(deadline {DEADLINE_SECONDS:.0f}s); last rejection: "
                + (rejected["detail"] if rejected else "none"))
            return body, trail

        draft = call(settings=settings, budget=budget,
                     messages=build(facts, rejected), schema=schema,
                     step=f"{kind}_report")
        body = draft.model_dump()
        # A copy, not the object itself. `body` later grows a `_trail` key that
        # points back at this list; storing the live object would make the
        # report contain itself and json.dumps would refuse it.
        trail.append({"step": "draft", "revision": attempt, "body": dict(body)})
        if trace:
            trace("draft", attempt, body.get("headline", ""))

        # Verdicts are arithmetic: set them from the counts before anything
        # else looks at the report, so the checker never spends a round trip
        # arguing about division. See verdict_for().
        corrected = enforce_verdicts(body, facts)
        dropped = enforce_pattern(body, facts)
        if dropped:
            corrected.append(dropped)
        # A clean concept has no mistakes to describe, so it carries no
        # sentence. Done before the checks so a cleared line cannot then be
        # rejected as a duplicate of another cleared line.
        corrected += strip_empty_evidence(body, facts)
        if corrected:
            trail.append({"step": "correct", "revision": attempt,
                          "body": {"corrections": corrected}})
            if trace:
                trace("correct", attempt, "; ".join(corrected))

        # Both checks are code, not a model call. citation and claim_strength
        # were both, in turn, judgement calls handed to a model and both, in
        # turn, measured to fail at it - see check_claim_strength()'s note for
        # the numbers. Nothing here asks a model to compare a sentence to a
        # count anymore.
        check = (check_citations(body, facts)
                 or check_distinct_evidence(body, facts)
                 or check_claim_strength(body, facts, kind))
        if check is None:
            check = _run_check(body, facts, kind, settings, budget,
                               store, budget_run, trail, trace, call=call)
        trail.append({"step": "check", "revision": attempt,
                      "body": check.model_dump()})
        if trace:
            trace("check", attempt,
                  check.verdict + (f" ({check.failed_check})" if check.failed_check else ""))

        if check.verdict == "accepted":
            body["_revisions"] = attempt
            return body, trail

        rejected = {"report": body, "failed_check": check.failed_check,
                    "detail": check.detail}

    # Budget spent without a clean draft. The last one ships, flagged - a report
    # that says it is uncertain is more use to a teacher than no report, but it
    # must not pretend it passed.
    body["_revisions"] = MAX_DRAFTS
    body["_unverified"] = rejected["detail"] if rejected else "check never passed"
    return body, trail


# ------------------------------------------------------------------- entry points

def for_student(store, student_id: str, settings, call=complete,
                force: bool = False, trace=None) -> dict:
    """The consolidated report a student sees after question 20.

    Cached: a second view of the same report is a database read, not another
    four model calls. `force=True` regenerates, which is the button a demo needs
    when a judge asks to watch it happen live.
    """
    if not force:
        cached = roster.load_report(store, "student", student_id)
        if cached:
            cached["_from_cache"] = True
            return cached

    facts = student_facts(store, student_id)
    run_id = store.create_run("recall_report",
                              meta={"student_id": student_id, "kind": "student"})
    store.set_state(run_id, RunState.DRAFTING)
    store.append(run_id, "facts", facts, produced_by="sql")

    body, trail = _generate(store, "student", student_id, facts, StudentReport,
                            build_student_messages, call, settings, run_id, trace)

    for row in trail:
        store.append(run_id, row["step"], row["body"],
                     produced_by=f"agent:{row['step']}")
    store.set_state(run_id, RunState.COMPLETE)

    body["_trail"] = trail
    roster.save_report(store, "student", student_id, body, run_id)
    body["_run_id"] = run_id
    # Set only on a run that actually just happened - never persisted, so a
    # LATER cached read of this same row correctly reports _from_cache=True
    # instead of remembering "fresh" forever. See _model_error_page's sibling
    # note in webapp.py for why this distinction exists: a plain page reload
    # replays this cache in ~1ms, no model involved, and nothing on screen
    # said so until this flag existed.
    body["_from_cache"] = False
    return body


def for_class(store, department: str, settings, call=complete,
              force: bool = False, trace=None) -> dict:
    """The teacher's per-class view. Same loop, different question."""
    if not force:
        cached = roster.load_report(store, "class", department)
        if cached:
            cached["_from_cache"] = True
            return cached

    facts = class_facts(store, department)
    run_id = store.create_run("recall_report",
                              meta={"department": department, "kind": "class"})
    store.set_state(run_id, RunState.DRAFTING)
    store.append(run_id, "facts", facts, produced_by="sql")

    body, trail = _generate(store, "class", department, facts, ClassReport,
                            build_class_messages, call, settings, run_id, trace)

    for row in trail:
        store.append(run_id, row["step"], row["body"],
                     produced_by=f"agent:{row['step']}")
    store.set_state(run_id, RunState.COMPLETE)

    body["_trail"] = trail
    roster.save_report(store, "class", department, body, run_id)
    body["_run_id"] = run_id
    body["_from_cache"] = False   # see the matching note in for_student()
    return body
