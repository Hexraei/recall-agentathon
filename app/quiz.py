"""The quiz bank: fixed questions, each wrong option pre-mapped to the exact
misconception it reveals.

This is the deliberate choice over a live model call at quiz-time. The point
tonight is to demonstrate PERSISTENT STATE - the system remembering a specific
person and using that memory later - and that story only lands if the thing
being remembered is itself reliable. A model inferring a misconception from a
bare option letter ("B") has almost nothing to work with, which is exactly
where a live failure would undermine the persistence story rather than the
demo just having a rough edge. So the diagnosis is decided here, at question-
writing time, by us - deterministic and fast. The live model work stays where
it is already proven: comparing a diagnosis against history, drafting a
bounded finding, checking it, and escalating to a professor when it matters.

Each concept maps onto the same misconceptions Mira and Arun already carry in
app/fixtures.py, so a tester's quiz result and the hand-written walkthrough
tell one consistent story, not two unrelated ones.
"""
from __future__ import annotations

from pydantic import BaseModel


class Option(BaseModel):
    key: str          # "A", "B", "C", "D"
    text: str
    correct: bool
    concept: str
    """Which learning objective this option is evidence about."""
    misconception: str | None
    """What picking this option reveals, in the same voice as a Finding
    statement - describes the work, never the person. None on the correct
    option, where there is nothing to diagnose."""


class Question(BaseModel):
    id: str
    prompt: str
    options: list[Option]

    def option(self, key: str) -> Option:
        for o in self.options:
            if o.key == key:
                return o
        raise KeyError(f"no option {key!r} on question {self.id}")


QUESTIONS: list[Question] = [
    Question(
        id="q_insertion_sort",
        prompt="What is the worst-case time complexity of insertion sort, "
               "and why?",
        options=[
            Option(key="A", text="O(n) — the outer loop runs n times",
                   correct=False, concept="counting work inside loops",
                   misconception=("counted only the outer loop's n iterations "
                                  "and did not account for the shifting work "
                                  "the inner loop does on each pass")),
            Option(key="B", text="O(n²) — the outer loop runs n times, and "
                                 "each pass may shift up to n elements",
                   correct=True, concept="counting work inside loops",
                   misconception=None),
            Option(key="C", text="O(log n) — the array is searched, not "
                                 "scanned",
                   correct=False, concept="relating loop structure to growth rate",
                   misconception=("applied logarithmic growth to a linear "
                                  "scan; nothing in insertion sort halves the "
                                  "remaining work")),
            Option(key="D", text="O(1) — insertion sort does not depend on "
                                 "input size",
                   correct=False, concept="relating loop structure to growth rate",
                   misconception=("treated the algorithm's cost as constant, "
                                  "with no relationship stated between input "
                                  "size and work done")),
        ],
    ),
    Question(
        id="q_dedup",
        prompt="Removing duplicates from a list by checking `if x not in "
               "result` for each of the n elements — what is the complexity "
               "of this approach?",
        options=[
            Option(key="A", text="O(n) — the loop goes through the list once",
                   correct=False, concept="counting work inside loops",
                   misconception=("counted only the visible loop and did not "
                                  "account for the work inside the membership "
                                  "test, which itself scans the result list")),
            Option(key="B", text="O(n²) — each of the n elements may trigger "
                                 "a scan of the growing result list",
                   correct=True, concept="counting work inside loops",
                   misconception=None),
            Option(key="C", text="O(n log n) — checking membership is like a "
                                 "sorted search",
                   correct=False, concept="justifying complexity claims from course material",
                   misconception=("assumed the membership check is a sorted "
                                  "search without evidence; `not in` on a list "
                                  "scans linearly, it does not binary search")),
            Option(key="D", text="O(1) — checking membership is instant",
                   correct=False, concept="justifying complexity claims from course material",
                   misconception=("assumed constant-time membership checking "
                                  "with no basis; `not in` on a list is not a "
                                  "hash lookup")),
        ],
    ),
    Question(
        id="q_binary_search",
        prompt="Binary search on a sorted array of n elements: what is its "
               "time complexity?",
        options=[
            Option(key="A", text="O(n) — there's still a loop that runs "
                                 "until it finds the answer",
                   correct=False, concept="relating loop structure to growth rate",
                   misconception=("treated the presence of a loop as evidence "
                                  "of linear growth, without asking how much "
                                  "of the problem the loop eliminates per pass")),
            Option(key="B", text="O(log n) — each comparison halves the "
                                 "remaining search space",
                   correct=True, concept="relating loop structure to growth rate",
                   misconception=None),
            Option(key="C", text="O(n²) — comparing the middle element takes "
                                 "n steps",
                   correct=False, concept="counting work inside loops",
                   misconception=("claimed each comparison itself costs n "
                                  "steps, with no justification — a single "
                                  "array index and comparison is constant time")),
            Option(key="D", text="O(1) — sorted arrays are searched instantly",
                   correct=False, concept="justifying complexity claims from course material",
                   misconception=("asserted constant time with no argument "
                                  "for why sorting would eliminate the search "
                                  "entirely")),
        ],
    ),
]


def by_id(question_id: str) -> Question:
    for q in QUESTIONS:
        if q.id == question_id:
            return q
    raise KeyError(f"no question {question_id!r}")


def to_attempt(student_id: str, question: Question, chosen_key: str) -> dict:
    """Turn one quiz answer into an Attempt record with its evidence already
    computed, so handle_extracting can skip the model entirely.

    The `passage` is what the tester chose, quoted rather than paraphrased -
    "chose option B: O(n²)..." - so the citation check still has something
    real to point at (the choice itself, made through this UI) even though
    there is no free prose to extract from. source_ref names the question and
    a timestamp-free run identity is left to the caller (student_id, assignment
    id below), matching the shape ingest.py already expects.
    """
    chosen = question.option(chosen_key)
    ref = f"{question.id}#{chosen_key}"

    if chosen.correct:
        items = [{
            "concept": chosen.concept, "kind": "strength",
            "passage": f"chose option {chosen_key}: {chosen.text}",
            "source_ref": ref, "supported": True, "note": None,
        }]
    else:
        items = [{
            "concept": chosen.concept, "kind": "difficulty",
            "passage": f"chose option {chosen_key}: {chosen.text}",
            "source_ref": ref, "supported": True, "note": None,
        }]

    return {
        "student_id": student_id,
        "assignment_id": question.id,
        "date": "",  # filled by the caller with the real timestamp
        "course_context": "Data Structures, live quiz",
        "assignment_prompt": question.prompt,
        "learning_objectives": sorted({o.concept for o in question.options}),
        "submission": f"chose option {chosen_key}: {chosen.text}",
        "precomputed_evidence": {
            "items": items,
            "uncertainty_notes": [],
            "unsupported_count": 0,
        },
        "quiz_meta": {
            "question_id": question.id,
            "chosen": chosen_key,
            "correct": chosen.correct,
            "misconception": chosen.misconception,
        },
    }
