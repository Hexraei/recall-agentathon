"""The records the steps pass each other.

Every boundary returns one of these, never a string. A bare list is not a
schema - where a step returns several of something it is wrapped in a model, so
the count bound lives where it is enforced rather than in a prompt where it is
a suggestion.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Attempt(BaseModel):
    """One submission. Written once per run, by ingest."""

    student_id: str
    assignment_id: str
    date: str
    course_context: str
    assignment_prompt: str
    learning_objectives: list[str] = Field(min_length=1)
    submission: str


class Evidence(BaseModel):
    concept: str
    kind: Literal["strength", "difficulty"]
    passage: str
    """Must appear verbatim in the source. Checked in code, never by a model."""
    source_ref: str
    supported: bool = True
    """Set False by the citation check when the passage could not be found.
    The row is kept and marked, never deleted - a citation that failed is a
    finding about the run."""
    note: str | None = None


class EvidenceSet(BaseModel):
    items: list[Evidence] = Field(min_length=1, max_length=8)
    uncertainty_notes: list[str] = Field(default_factory=list, max_length=5)


class Comparison(BaseModel):
    label: Literal["similar", "recurring", "improving", "not_enough_evidence"]
    related_refs: list[str] = Field(default_factory=list, max_length=10)
    explanation: str


class Finding(BaseModel):
    revision: int
    status: Literal["first_signal", "candidate_recurring",
                    "confirmed_recurring", "improving"]
    statement: str
    supporting_refs: list[str] = Field(default_factory=list, max_length=10)
    uncertainty: str
    proposed_next_step: str


class Check(BaseModel):
    verdict: Literal["accepted", "rejected", "needs_review"]
    failed_check: Literal["citation", "claim_strength", "comparison_validity"] | None = None
    detail: str = ""


class Review(BaseModel):
    decision: Literal["confirm", "revise", "reject", "request_more_evidence", "no_reply"]
    instructional_note: str | None = None
