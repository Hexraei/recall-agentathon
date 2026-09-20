"""Tests for the quiz app: the bank's shape, the roster's counting, and the
report agent's two gates.

The counting tests matter more than they look. The report agent is TOLD the
counts and asked only to interpret them - so if roster.by_concept miscounts,
the model will interpret a wrong number with complete confidence and nothing
downstream will catch it. These tests are the only thing standing there.
"""
from __future__ import annotations

import json

import pytest

from app import bank, report, roster
from slice.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.db")
    roster.init(s)
    return s


# ---------------------------------------------------------------- the bank

def test_each_department_has_twenty_questions_in_five_topics():
    for dept in bank.DEPARTMENTS:
        qs = bank.for_department(dept)
        assert len(qs) == 20, dept
        topics = bank.topics(dept)
        assert len(topics) == 5, (dept, topics)
        for t in topics:
            assert sum(1 for q in qs if q.topic == t) == 4, (dept, t)


def test_every_question_has_one_correct_option_and_four_choices():
    for q in bank.ALL:
        assert len(q.options) == 4, q.id
        assert sum(o.correct for o in q.options) == 1, q.id


def test_the_answer_key_is_spread_across_all_four_letters():
    """Every question is authored with the correct option second, which made B
    correct on all 40. The first end-to-end run scored 20/20 by answering B on
    everything - a tester who notices that has a perfect score and the data is
    worthless."""
    from collections import Counter
    for dept in bank.DEPARTMENTS:
        keys = Counter(q.answer_key for q in bank.for_department(dept))
        assert set(keys) == {"A", "B", "C", "D"}, (dept, keys)
        # No letter may carry more than half the questions.
        assert max(keys.values()) <= 10, (dept, keys)


def test_options_are_labelled_a_to_d_in_order():
    for q in bank.ALL:
        assert [o.key for o in q.options] == ["A", "B", "C", "D"], q.id


def test_the_answer_key_is_stable_for_a_given_question():
    """Rotation is by question id, not random: the same student sees the same
    layout on a reload, and two students' answers stay comparable."""
    assert bank.by_id("rb_t1_q1").answer_key == bank.by_id("rb_t1_q1").answer_key
    first = {q.id: q.answer_key for q in bank.ALL}
    import importlib
    importlib.reload(bank)
    assert {q.id: q.answer_key for q in bank.ALL} == first


def test_every_wrong_option_names_a_misconception_and_no_right_one_does():
    """The misconception mapping IS the diagnosis - a wrong option without one
    is a question that teaches the report nothing."""
    for q in bank.ALL:
        for o in q.options:
            assert (o.misconception is None) == o.correct, (q.id, o.key)


def test_every_concept_spans_at_least_two_topics():
    """The whole cross-topic story depends on this. A concept confined to one
    topic can never show that one cause is behind trouble in several places,
    which is the only thing this report does that a scoreboard does not."""
    for dept in bank.DEPARTMENTS:
        spanning = {}
        for q in bank.for_department(dept):
            spanning.setdefault(q.concept, set()).add(q.topic)
        for concept, topics in spanning.items():
            assert len(topics) >= 2, (dept, concept, topics)


def test_every_concept_has_at_least_three_questions():
    """Two questions cannot separate a gap from a slip, so verdict_for() calls
    any such concept `mixed` whatever the answers. The first robotics bank had
    several, and the report it produced said `mixed` seven times in a row and
    found no pattern at all - a page that told the student nothing."""
    for dept in bank.DEPARTMENTS:
        counts = {}
        for q in bank.for_department(dept):
            counts[q.concept] = counts.get(q.concept, 0) + 1
        for concept, n in counts.items():
            assert n >= 3, (dept, concept, n)


# --------------------------------------------------------------- the roster

def _widest(dept: str) -> str:
    """The concept covering the most topics in a department.

    Derived from the bank rather than named as a literal. These tests are about
    the MACHINERY - grouping, counting, cross-topic detection - not about any
    particular concept, and hard-coded names broke every one of them the first
    time the bank was rewritten for readability.
    """
    spanning: dict[str, set] = {}
    for q in bank.for_department(dept):
        spanning.setdefault(q.concept, set()).add(q.topic)
    return max(spanning, key=lambda c: (len(spanning[c]), c))


def _count_for(dept: str, concept: str) -> int:
    return sum(1 for q in bank.for_department(dept) if q.concept == concept)


def _answer_all(store, sid, dept, wrong_concepts=frozenset()):
    for q in bank.for_department(dept):
        wrong = q.concept in wrong_concepts
        key = (next(o.key for o in q.options if not o.correct) if wrong
               else q.answer_key)
        roster.record(store, sid, q, key)


def test_a_student_is_looked_up_by_register_number_not_duplicated(store):
    a = roster.create_student(store, "A", "1", "REG1", "computer_science")
    b = roster.create_student(store, "A", "1", "REG1", "computer_science")
    assert a == b
    assert len(roster.students_in(store, "computer_science")) == 1


def test_answering_the_same_question_twice_keeps_the_first(store):
    """Insert-only. A refresh or a back button must not turn one answer into
    two rows, or every count downstream is wrong."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    q = bank.by_id("cs_t1_q1")
    roster.record(store, sid, q, q.answer_key)
    roster.record(store, sid, q, "A")
    got, asked = roster.score(store, sid)
    assert (got, asked) == (1, 1)


def test_by_concept_groups_across_topics(store):
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})

    rows = {r["concept"]: r for r in roster.by_concept(store, sid)}
    loops = rows[_widest("computer_science")]
    assert loops["correct"] == 0
    assert loops["asked"] == _count_for("computer_science",
                                        _widest("computer_science"))
    # The point of the whole design: one concept, several topics.
    assert len(loops["topics"]) >= 3, loops["topics"]


def test_score_and_topic_counts_agree(store):
    sid = roster.create_student(store, "A", "1", "R", "robotics")
    _answer_all(store, sid, "robotics",
                wrong_concepts={_widest("robotics")})
    got, asked = roster.score(store, sid)
    assert asked == 20
    assert got == 20 - _count_for("robotics", _widest("robotics"))
    assert sum(t["asked"] for t in roster.by_topic(store, sid)) == 20
    assert sum(t["correct"] for t in roster.by_topic(store, sid)) == got


def test_class_common_wrong_counts_students_converging_on_one_option(store):
    """A shared misconception is students landing on the SAME wrong option.
    That count is what separates a teaching problem from a tutoring one."""
    for i in range(3):
        sid = roster.create_student(store, f"S{i}", "1", f"R{i}", "computer_science")
        _answer_all(store, sid, "computer_science",
                    wrong_concepts={_widest("computer_science")})

    common = roster.class_common_wrong(store, "computer_science")
    assert common, "no shared wrong answers found"
    assert common[0]["n"] == 3
    assert roster.class_size(store, "computer_science") == 3


def test_students_in_one_department_do_not_pollute_the_other(store):
    a = roster.create_student(store, "A", "1", "R1", "computer_science")
    b = roster.create_student(store, "B", "1", "R2", "robotics")
    _answer_all(store, a, "computer_science")
    _answer_all(store, b, "robotics")
    assert roster.class_size(store, "computer_science") == 1
    assert roster.class_size(store, "robotics") == 1
    cs_concepts = {r["concept"] for r in roster.class_by_concept(store, "computer_science")}
    rb_concepts = {r["concept"] for r in roster.class_by_concept(store, "robotics")}
    # "justifying claims with a concrete argument" is deliberately in both;
    # everything else must stay on its own side.
    assert cs_concepts != rb_concepts


# --------------------------------------------------- verdicts are arithmetic

@pytest.mark.parametrize("correct,asked,want", [
    (5, 5, "strong"),    # all of them
    (4, 5, "strong"),    # all but one, out of 5
    (3, 4, "strong"),    # all but one, out of 4
    (2, 3, "mixed"),     # all but one, out of 3 - too few to call it strong
    (0, 3, "weak"),
    (1, 3, "weak"),
    (1, 5, "weak"),
    (3, 5, "mixed"),
    (0, 2, "mixed"),     # two questions cannot separate a gap from a slip
    (2, 2, "mixed"),
    (0, 1, "mixed"),
    # Class scale: `asked` is every answer from every student, so the
    # thresholds go proportional. An absolute "one or none" rule called 2 of 30
    # `mixed`, and "all but one" called 29 of 30 `strong` - neither is the
    # claim a teacher would recognise.
    (2, 30, "weak"),
    (10, 30, "weak"),
    (15, 30, "mixed"),
    (24, 30, "strong"),
    (29, 30, "strong"),
    (10, 12, "strong"),
])
def test_verdict_is_computed_from_the_counts(correct, asked, want):
    """The rule both models kept getting wrong. A full cohort run put EVERY
    report at the redraft ceiling, with the writer calling 4-of-5 'weak' and
    the checker calling 0-of-3 'strong'. Division is not a judgement call."""
    assert report.verdict_for(correct, asked) == want


def test_a_wrong_verdict_is_corrected_not_rejected(store):
    """Nothing gets sent back over a verdict any more - it is simply set
    right, which is faster than a round trip and cannot fail."""
    facts = {"by_concept": [
        {"concept": "loops", "asked": 5, "correct": 4},
        {"concept": "refs", "asked": 3, "correct": 0},
    ]}
    body = {"gaps": [{"concept": "loops", "verdict": "weak", "evidence": "x"},
                     {"concept": "refs", "verdict": "strong", "evidence": "y"}],
            "strengths": []}

    fixed = report.enforce_verdicts(body, facts)

    # loops (4 of 5) is strong, so it leaves gaps; refs (0 of 3) is weak and
    # belongs exactly where it already was.
    assert [r["concept"] for r in body["strengths"]] == ["loops"]
    assert [r["concept"] for r in body["gaps"]] == ["refs"]
    assert body["strengths"][0]["verdict"] == "strong"
    assert body["gaps"][0]["verdict"] == "weak"
    assert len(fixed) == 2
    assert any("loops" in f and "4 of 5" in f for f in fixed)


def test_a_strong_concept_filed_under_gaps_is_moved_not_just_relabelled(store):
    """The half that is easy to forget. Correcting a 4-of-5 concept to `strong`
    while leaving it under `gaps` produces "gap: strong" - a contradiction the
    checker rejected on EVERY draft, which is what pinned reports at the
    redraft ceiling until the entry moved lists too."""
    facts = {"by_concept": [{"concept": "loops", "asked": 5, "correct": 4}]}
    body = {"gaps": [{"concept": "loops", "verdict": "weak", "evidence": "x"}],
            "strengths": []}

    fixed = report.enforce_verdicts(body, facts)

    assert body["gaps"] == []
    assert len(body["strengths"]) == 1
    assert body["strengths"][0]["verdict"] == "strong"
    assert "moved gaps -> strengths" in fixed[0]


def test_a_weak_concept_filed_under_strengths_is_moved(store):
    facts = {"by_concept": [{"concept": "refs", "asked": 3, "correct": 0}]}
    body = {"strengths": [{"concept": "refs", "verdict": "strong", "evidence": "x"}]}

    report.enforce_verdicts(body, facts)

    assert body["strengths"] == []
    assert body["gaps"][0]["verdict"] == "weak"


def test_the_class_lists_move_the_same_way(store):
    facts = {"by_concept": [{"concept": "loops", "answered": 30, "asked": 30,
                             "correct": 2}]}
    body = {"solid": [{"concept": "loops", "verdict": "strong", "evidence": "x"}]}
    report.enforce_verdicts(body, facts)
    assert body["solid"] == []
    assert body["teach_again"][0]["verdict"] == "weak"


def test_a_mixed_concept_stays_where_the_model_put_it(store):
    """Mixed is legitimately reportable as either a soft strength or a soft
    gap. That IS a judgement call, unlike the arithmetic, so code leaves it."""
    facts = {"by_concept": [{"concept": "c", "asked": 5, "correct": 3}]}
    body = {"gaps": [{"concept": "c", "verdict": "weak", "evidence": "x"}]}
    report.enforce_verdicts(body, facts)
    assert len(body["gaps"]) == 1
    assert body["gaps"][0]["verdict"] == "mixed"


def test_no_corrections_reported_when_nothing_changed(store):
    """A no-op must not show up in the trail as a correction, or the
    'how this was produced' panel fills with noise that means nothing."""
    facts = {"by_concept": [{"concept": "loops", "asked": 5, "correct": 0}]}
    body = {"gaps": [{"concept": "loops", "verdict": "weak", "evidence": "x"}]}
    assert report.enforce_verdicts(body, facts) == []


def test_verdict_correction_reads_class_counts_too(store):
    """class_by_concept spells the total `answered`; by_concept spells it
    `asked`. One rule reads both, so both must carry the same key or the rule
    silently applies to half its inputs."""
    for i in range(3):
        sid = roster.create_student(store, f"S{i}", "1", f"R{i}", "computer_science")
        _answer_all(store, sid, "computer_science",
                    wrong_concepts={_widest("computer_science")})
    rows = roster.class_by_concept(store, "computer_science")
    assert all("asked" in r for r in rows)
    assert all(r["asked"] == r["answered"] for r in rows)

    facts = {"by_concept": rows}
    body = {"teach_again": [{"concept": _widest("computer_science"),
                             "verdict": "strong", "evidence": "x"}]}
    report.enforce_verdicts(body, facts)
    assert body["teach_again"][0]["verdict"] == "weak"   # 0 of 15


def test_correction_leaves_an_invented_concept_for_the_citation_gate(store):
    """enforce_verdicts must not crash or silently invent counts for a concept
    nobody answered - that is the citation gate's job, and it runs next."""
    facts = {"by_concept": [{"concept": "real", "asked": 4, "correct": 4}]}
    body = {"gaps": [{"concept": "invented", "verdict": "weak", "evidence": "x"}]}
    assert report.enforce_verdicts(body, facts) == []
    assert body["gaps"][0]["verdict"] == "weak"          # untouched
    assert report.check_citations(body, facts).failed_check == "citation"


# ------------------------------------------------------- the citation gate

def test_citation_gate_rejects_a_concept_the_student_never_answered(store):
    """The code-side half of the check. A model naming a plausible-sounding
    concept nobody was asked about must not reach a teacher."""
    facts = {"by_concept": [{"concept": "counting work inside loops",
                             "asked": 5, "correct": 0}]}
    bad = {"gaps": [{"concept": "graph traversal", "verdict": "weak",
                     "evidence": "made it up"}]}
    check = report.check_citations(bad, facts)
    assert check is not None
    assert check.verdict == "rejected"
    assert check.failed_check == "citation"
    assert "graph traversal" in check.detail


def test_citation_gate_passes_a_real_concept(store):
    facts = {"by_concept": [{"concept": "counting work inside loops",
                             "asked": 5, "correct": 0}]}
    good = {"gaps": [{"concept": "counting work inside loops",
                      "verdict": "weak", "evidence": "0 of 5"}]}
    assert report.check_citations(good, facts) is None


def test_citation_gate_reads_every_list_a_report_can_cite_from(store):
    """strengths, gaps, teach_again and solid all name concepts. Checking only
    one of them would leave three doors open."""
    facts = {"by_concept": [{"concept": "real", "asked": 4, "correct": 2}]}
    for field in ("strengths", "gaps", "teach_again", "solid"):
        bad = {field: [{"concept": "invented", "verdict": "weak", "evidence": "x"}]}
        check = report.check_citations(bad, facts)
        assert check is not None and check.failed_check == "citation", field


# ------------------------------------------- the draft/check loop, no network

class _Scripted:
    """A canned `call` so the loop can be tested with no key and no tokens."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, *, settings, budget, messages, schema, step):
        self.calls.append(step)
        return schema.model_validate(self.replies.pop(0))


_CS_CONCEPT = _widest("computer_science")

_FACTS_STUDENT = {
    "department": "computer_science",
    "score": {"correct": 15, "asked": 20},
    "by_topic": [], "wrong_answers": [],
    "by_concept": [{"concept": _CS_CONCEPT, "asked": 5,
                    "correct": 0, "topics": ["Recursion", "Time Complexity"]}],
    "class_average_by_concept": [], "class_size": 1,
}

_OK_REPORT = {
    "headline": "One gap, several topics.",
    "strengths": [], "gaps": [{"concept": _CS_CONCEPT,
                               "verdict": "weak", "evidence": "0 of 5"}],
    "cross_topic_pattern": "Same cause in Recursion and Time Complexity.",
    "next_step": "Trace nested loops by hand.",
    "uncertainty": "Twenty multiple-choice questions cannot show reasoning.",
}


def test_an_accepted_draft_stops_the_loop(store):
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})
    call = _Scripted(_OK_REPORT)

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == 1
    # The check is code now (see check_claim_strength) - a clean draft costs
    # exactly one model call, not two.
    assert call.calls == ["student_report"]
    assert "_unverified" not in body


def test_a_rejection_sends_the_draft_back_with_the_reason(store):
    """The back-edge. The second request must carry the objection - a blind
    retry of an identical prompt usually fails identically.

    The rejection itself comes from check_claim_strength (code), triggered by
    a real overclaim in the draft body, not a scripted checker reply - the
    checker is no longer a model call.
    """
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})

    overclaim = dict(_OK_REPORT, headline="You got 20 of 20 questions right.")
    call = _Scripted(overclaim, _OK_REPORT)

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == 2
    # Found by step name, not position: a `correct` row appears between a draft
    # and its check whenever code fixed a verdict or dropped a pattern.
    steps = [r["step"] for r in body["_trail"]]
    assert steps.count("draft") == 2
    checks = [r["body"] for r in body["_trail"] if r["step"] == "check"]
    assert checks[0]["verdict"] == "rejected"
    assert steps.index("draft") < steps.index("check")


def test_the_rejection_detail_reaches_the_next_prompt(store):
    reason = "The pattern is not traceable to specific rows."
    msgs = report.build_student_messages(
        _FACTS_STUDENT,
        {"report": _OK_REPORT, "failed_check": "claim_strength", "detail": reason})
    text = msgs[-1]["content"]
    assert "REJECTED" in text
    assert reason in text


def test_a_report_that_never_passes_ships_flagged_not_silently(store):
    """Spending the whole redraft budget still ships the last draft - a teacher
    is better served by a flagged report than by nothing - but it must not look
    like it passed.

    Every scripted draft repeats the same real overclaim, so check_claim_strength
    (code) rejects it every time - scripted from MAX_DRAFTS rather than a
    hard-coded 3, so tuning the budget does not silently turn this into a test
    of nothing."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})
    overclaim = dict(_OK_REPORT, headline="You got 20 of 20 questions right.")
    call = _Scripted(*([overclaim] * report.MAX_DRAFTS))

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == report.MAX_DRAFTS
    assert "20 of 20" in body["_unverified"]
    assert not call.replies, "the loop stopped early"


def test_a_slow_report_stops_at_the_deadline_and_ships_what_it_has(store, monkeypatch):
    """The wall-clock fence. During a network drop one report stacked
    per-request timeouts to ~40 minutes; no per-call timeout was wrong, they
    simply composed. MAX_DRAFTS cannot catch that because the time goes INSIDE
    one draft's call chain, so the deadline is a third, separate counter."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})

    # A real overclaim, so check_claim_strength (code) rejects every draft -
    # the check itself is no longer a model call, so only draft replies are
    # scripted here.
    overclaim = dict(_OK_REPORT, headline="You got 20 of 20 questions right.")
    call = _Scripted(overclaim, overclaim, overclaim)

    # A clock that jumps past the deadline once the first draft has been
    # written. Driven by the scripted call rather than by a call count, because
    # the store writes timestamps too and counting reads is fragile.
    import time as _t
    real = _t.time
    late = {"yes": False}
    monkeypatch.setattr(
        _t, "time", lambda: real() + (report.DEADLINE_SECONDS * 10 if late["yes"] else 0))

    inner = call

    def _call(**kw):
        result = inner(**kw)
        if kw["step"].endswith("_report"):
            late["yes"] = True      # a draft has now been produced: time flies
        return result

    body = report.for_student(store, sid, settings=None, call=_call, force=True)
    assert body["_revisions"] == 1, "kept drafting past the deadline"
    assert "deadline" in body["_unverified"]
    # It still shipped a usable report rather than raising.
    assert body["headline"] == overclaim["headline"]
    assert len(call.replies) == 2, "should have stopped after the first draft"


def test_a_cached_report_does_not_call_the_model_again(store):
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science")
    call = _Scripted(_OK_REPORT, {"verdict": "accepted"})
    report.for_student(store, sid, settings=None, call=call, force=True)

    def _blow_up(**kw):
        raise AssertionError("cached report still called the model")

    again = report.for_student(store, sid, settings=None, call=_blow_up)
    assert again["headline"] == _OK_REPORT["headline"]


def test_a_student_report_never_sees_another_student(store):
    """No peer comparison, no class average, no ranking. A student's diagnosis
    rests on their own work or it is not a diagnosis."""
    a = roster.create_student(store, "A", "1", "R1", "computer_science")
    b = roster.create_student(store, "B", "1", "R2", "computer_science")
    _answer_all(store, a, "computer_science",
                wrong_concepts={_widest("computer_science")})
    _answer_all(store, b, "computer_science")     # a perfect scorer alongside

    facts = report.student_facts(store, a)
    blob = json.dumps(facts)
    assert "class_average_by_concept" not in facts
    assert "class_size" not in facts
    assert b not in blob, "another student's id reached a student report"
    # Only this student's own counts are present.
    assert facts["score"]["asked"] == 20
    assert set(facts) == {"department", "score", "by_topic", "by_concept"}


def test_the_two_departments_never_mix(store):
    """Separate questions, separate concepts, separate reports. A robotics
    student's numbers must not move a CS report, in either direction."""
    cs = roster.create_student(store, "C", "1", "R1", "computer_science")
    rb = roster.create_student(store, "R", "1", "R2", "robotics")
    _answer_all(store, cs, "computer_science")
    _answer_all(store, rb, "robotics", wrong_concepts={
        _widest("robotics")})

    cs_facts = report.class_facts(store, "computer_science")
    rb_facts = report.class_facts(store, "robotics")
    assert cs_facts["students"] == 1 and rb_facts["students"] == 1

    cs_concepts = {r["concept"] for r in cs_facts["by_concept"]}
    assert _widest("robotics") not in cs_concepts
    cs_topics = {r["topic"] for r in cs_facts["by_topic"]}
    assert cs_topics.isdisjoint({r["topic"] for r in rb_facts["by_topic"]})

    # The robotics student's wrong answers are absent from the CS class view.
    assert all("rb_" not in q["question_id"] for q in cs_facts["hardest_questions"])


def test_the_facts_handed_to_the_model_come_from_sql_not_the_model(store):
    """The model interprets counts; it never produces them. If this ever
    inverts, a miscount becomes a confident diagnosis with nothing to catch it.
    """
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={_widest("computer_science")})
    facts = report.student_facts(store, sid)
    n = _count_for("computer_science", _widest("computer_science"))
    assert facts["score"] == {"correct": 20 - n, "asked": 20}
    loops = next(r for r in facts["by_concept"]
                 if r["concept"] == _widest("computer_science"))
    # Every number the writer needs sits in the row it belongs to, so it never
    # has to match a flat list against a count and never has to add anything up.
    assert loops["asked"] == n and loops["correct"] == 0
    assert loops["verdict"] == "weak"
    assert loops["wrong_answer_count"] == n
    assert len(loops["wrong_answers"]) == loops["wrong_answer_count"]
    assert len(loops["missed_in_topics"]) >= 3
    assert "topics" not in loops, "two keys for one fact invites a mismatch"


# ----------------------------------------- claim_strength, in code (not a model)

# The four rejections below are verbatim from demo.db, written by the checker
# MODEL against reports that were factually correct. Each one is a sentence the
# counts support, rejected as false - including "the counts show 8 correct out
# of 20 asked" used to reject a headline reading "You got 8 of 20 questions
# right". They are the measurement that moved this check into code, and they
# are here so a future rewrite has to survive them.

def test_true_sentences_the_checker_model_used_to_reject_are_accepted():
    cases = [
        ("a clean sweep that really is clean",
         {"headline": "A solid run.",
          "strengths": [{"concept": "singularities", "verdict": "strong",
                         "evidence": "All the answers here were right."}],
          "gaps": [], "next_step": "x", "uncertainty": "y"},
         {"score": {"correct": 15, "asked": 20},
          "by_concept": [{"concept": "singularities", "asked": 3, "correct": 3,
                          "wrong_answer_count": 0, "missed_in_topics": []}]}),
        ("a headline quoting the score exactly",
         {"headline": "You got 8 of 20 questions right.",
          "strengths": [], "gaps": [], "next_step": "x", "uncertainty": "y"},
         {"score": {"correct": 8, "asked": 20}, "by_concept": []}),
        ("prose restating a fact that supports it",
         {"headline": "Only one topic came through clean.",
          "strengths": [], "gaps": [], "next_step": "x", "uncertainty": "y"},
         {"score": {"correct": 12, "asked": 20}, "by_concept": [],
          "by_topic": [{"topic": "Memory & State", "asked": 4, "correct": 4}]}),
    ]
    for name, body, facts in cases:
        assert report.check_claim_strength(body, facts) is None, name


def test_a_genuinely_false_claim_is_still_rejected():
    facts = {"score": {"correct": 8, "asked": 20},
             "by_concept": [{"concept": "loops", "asked": 3, "correct": 2,
                             "wrong_answer_count": 1,
                             "missed_in_topics": ["Lists and Loops"]}]}
    base = {"headline": "Good work.", "strengths": [], "gaps": [],
            "next_step": "x", "uncertainty": "y"}

    sweep = dict(base, strengths=[{"concept": "loops", "verdict": "strong",
                                   "evidence": "You got all of these right."}])
    assert report.check_claim_strength(sweep, facts).failed_check == "claim_strength"

    wrong_score = dict(base, headline="You got 18 of 20 questions right.")
    assert report.check_claim_strength(wrong_score, facts) is not None

    ranked = dict(base, headline="You scored below average for the class.")
    assert report.check_claim_strength(ranked, facts) is not None

    personal = dict(base, next_step="You are careless; slow down.")
    assert report.check_claim_strength(personal, facts) is not None


def test_an_over_long_field_is_trimmed_rather_than_losing_the_report():
    """Measured: one report's entire SchemaFailure was a single `evidence`
    field 192 characters long against a 160 bound. The reply was complete and
    well formed - finish_reason "stop", not "length" - so this is not the
    truncation bug. Discarding a student's only feedback over 32 characters is
    the wrong trade; trimming to a word boundary is not."""
    import json as _json
    from slice.llm import _parse, _parse_or_trim

    long_evidence = ("The misses treated the Jacobian as failing to exist, "
                     "inverted it anyway, and assumed a unique solution existed "
                     "near the singular configuration where the arm loses a "
                     "degree of freedom entirely.")
    assert len(long_evidence) > 160
    body = {"headline": "You got 13 of 20 right.",
            "strengths": [],
            "gaps": [{"concept": "c", "verdict": "weak", "evidence": long_evidence}],
            "next_step": "x.", "uncertainty": "y."}
    text = _json.dumps(body)

    assert _parse(text, report.StudentReport) is None, "should fail without salvage"
    out = _parse_or_trim(text, report.StudentReport)
    assert out is not None, "an over-long field must not cost the whole report"
    assert len(out.gaps[0].evidence) <= 160
    assert out.gaps[0].evidence.endswith("."), "must read as a finished sentence"
    assert not out.gaps[0].evidence.endswith(" .")
    assert out.headline == body["headline"], "nothing else may be touched"


def test_trimming_does_not_rescue_a_structurally_wrong_reply():
    """Only length is salvaged. A missing field, a bad enum or a wrong type is
    a real disagreement about the contract and must still fail - those change
    what the report SAYS, where a trimmed sentence only says it shorter."""
    import json as _json
    from slice.llm import _parse_or_trim

    for broken in ({"headline": "x"},
                   {"headline": "x", "strengths": ["a bare string"], "gaps": [],
                    "next_step": "n", "uncertainty": "u"},
                   {"headline": "x", "strengths": [], "next_step": "n",
                    "uncertainty": "u",
                    "gaps": [{"concept": "c", "verdict": "excellent",
                              "evidence": "e"}]}):
        assert _parse_or_trim(_json.dumps(broken), report.StudentReport) is None


def test_a_sentence_that_admits_its_miss_is_not_a_clean_sweep_claim():
    """Verbatim from a measured run, and a false positive this check itself
    caused before the rule was tightened: on a 4-of-5 concept it rejected a
    sentence that explicitly ADMITS the miss, because the phrase "every time"
    appeared in a clause describing the misconception rather than the student.

    That is the same false rejection the checker model was making, reproduced
    in code - which is the failure mode this whole check exists to end, so it
    is pinned here."""
    facts = {"score": {"correct": 17, "asked": 20},
             "by_concept": [{"concept": "counting work inside loops", "asked": 5,
                             "correct": 4, "wrong_answer_count": 1,
                             "missed_in_topics": ["Lists and Loops"]}]}
    body = {"headline": "A strong run with one thing to tidy up.",
            "strengths": [{"concept": "counting work inside loops",
                           "verdict": "strong",
                           "evidence": "The one miss assumed every append "
                                       "reallocates; amortised growth means "
                                       "copies happen rarely, not every time."}],
            "gaps": [], "next_step": "x", "uncertainty": "y"}
    assert report.check_claim_strength(body, facts) is None

    # But the same concept with a real sweep claim is still caught.
    overclaim = dict(body, strengths=[
        {"concept": "counting work inside loops", "verdict": "strong",
         "evidence": "You got all of these right."}])
    assert report.check_claim_strength(overclaim, facts) is not None


def test_domain_vocabulary_is_not_mistaken_for_a_ranking_or_an_insult():
    """Both verbatim false positives this check caused before the phrase lists
    were tightened. A bare "rank" matched "rank-deficient" in a robotics report
    about Jacobian singularities; "smart" sits inside "smart pointer". Short
    substrings that fit inside a technical term reproduce, in code, exactly the
    false rejections the checker model was making."""
    class_facts = {"by_concept": [
        {"concept": "singularities", "asked": 12, "correct": 6,
         "wrong_answer_count": 6, "missed_in_topics": ["Kinematics", "Control"]}]}
    jacobian = {"headline": "One concept needs re-teaching.",
                "teach_again": [{"concept": "singularities", "verdict": "weak",
                                 "evidence": "Students treated the Jacobian as "
                                             "failing to exist, missing that it "
                                             "is simply rank-deficient."}],
                "solid": [], "next_step": "x", "uncertainty": "y"}
    assert report.check_claim_strength(jacobian, class_facts, "class") is None

    stu_facts = {"score": {"correct": 8, "asked": 20}, "by_concept": []}
    pointer = {"headline": "Good work.", "strengths": [], "gaps": [],
               "next_step": "Review how a smart pointer releases its memory.",
               "uncertainty": "y"}
    assert report.check_claim_strength(pointer, stu_facts, "student") is None


def test_cohort_language_is_descriptive_on_a_class_report_only():
    """A class report is ABOUT the cohort, so "most students" describes it. The
    same phrase on a student report ranks them against classmates, which is
    data that report is deliberately never given."""
    class_facts = {"by_concept": []}
    cohort = {"headline": "Most students missed this concept.",
              "teach_again": [], "solid": [], "next_step": "x", "uncertainty": "y"}
    assert report.check_claim_strength(cohort, class_facts, "class") is None

    stu_facts = {"score": {"correct": 8, "asked": 20}, "by_concept": []}
    ranked = {"headline": "You did better than most students.",
              "strengths": [], "gaps": [], "next_step": "x", "uncertainty": "y"}
    assert report.check_claim_strength(ranked, stu_facts, "student") is not None


# ------------------------------------ evidence: one sentence, about one concept

def test_a_concept_with_no_mistakes_carries_no_sentence():
    """`evidence` reads the WRONG ANSWERS. A concept with none leaves the model
    nothing to say, and asked anyway it writes filler - "You got all of these
    right" appeared 55 times across 150 entries on the real cohort, beside a
    score already showing 3/3. Cleared in code, like enforce_pattern(): no
    rewrite can turn an absent mistake into an observation about one."""
    facts = {"by_concept": [
        {"concept": "clean", "asked": 3, "correct": 3, "wrong_answer_count": 0,
         "missed_in_topics": []},
        {"concept": "messy", "asked": 4, "correct": 1, "wrong_answer_count": 3,
         "missed_in_topics": ["A", "B"]}]}
    body = {"headline": "h",
            "strengths": [{"concept": "clean", "verdict": "strong",
                           "evidence": "You got all of these right."}],
            "gaps": [{"concept": "messy", "verdict": "weak",
                      "evidence": "The misses counted the outer loop only."}],
            "next_step": "n", "uncertainty": "u"}

    notes = report.strip_empty_evidence(body, facts)
    assert body["strengths"][0]["evidence"] == ""
    assert any("clean" in n for n in notes)
    # A concept that DOES have mistakes keeps its sentence.
    assert body["gaps"][0]["evidence"] == "The misses counted the outer loop only."


def test_one_sentence_may_not_stand_in_for_two_concepts():
    """Measured: a sentence was reused across different concepts 36 times in 30
    real reports. Sometimes generic, sometimes a specific reading of one
    concept's mistakes pasted onto another's - which says something false about
    the second. Unlike the filler case this is sent BACK: the mistakes are
    there to describe, the model just described them once."""
    facts = {"by_concept": [
        {"concept": "a", "asked": 4, "correct": 1, "wrong_answer_count": 3,
         "missed_in_topics": ["X"]},
        {"concept": "b", "asked": 4, "correct": 1, "wrong_answer_count": 3,
         "missed_in_topics": ["Y"]}]}
    shared = "The misses both missed a continuous effect."
    body = {"headline": "h", "strengths": [],
            "gaps": [{"concept": "a", "verdict": "weak", "evidence": shared},
                     {"concept": "b", "verdict": "weak", "evidence": shared}],
            "next_step": "n", "uncertainty": "u"}

    check = report.check_distinct_evidence(body, facts)
    assert check is not None and check.failed_check == "claim_strength"
    assert "a" in check.detail and "b" in check.detail

    # Distinct sentences pass.
    body["gaps"][1]["evidence"] = "The misses chose the average, not the worst case."
    assert report.check_distinct_evidence(body, facts) is None

    # Two EMPTY sentences are not duplicates - both concepts were simply clean.
    body["gaps"][0]["evidence"] = ""
    body["gaps"][1]["evidence"] = ""
    assert report.check_distinct_evidence(body, facts) is None


def test_the_results_page_omits_an_empty_sentence_rather_than_printing_a_blank():
    import webapp
    rows = [{"concept": "clean", "verdict": "strong", "evidence": ""},
            {"concept": "messy", "verdict": "weak", "evidence": "The misses skipped it."}]
    html = webapp._concept_cards(rows, "ok")
    assert "<p" not in html.split("messy")[0], "empty evidence rendered a paragraph"
    assert "The misses skipped it." in html


def test_the_trail_shows_what_code_corrected_not_a_blank_check_line():
    """The `correct` step is where arithmetic - not judgement - fixed the
    draft: a verdict recomputed, an entry moved, filler cleared. It used to
    fall through to the check branch and render as "check r1 -> " with nothing
    after it, which is both wrong and hides the most interesting line in the
    trail."""
    import webapp
    body = {"_revisions": 2, "_trail": [
        {"step": "draft", "revision": 1, "body": {"headline": "first try"}},
        {"step": "check", "revision": 1,
         "body": {"verdict": "rejected", "failed_check": "citation",
                  "detail": "named a topic, not a concept"}},
        {"step": "draft", "revision": 2, "body": {"headline": "second try"}},
        {"step": "correct", "revision": 2,
         "body": {"corrections": ["loops: weak -> strong (4 of 4), moved gaps -> strengths"]}},
        {"step": "check", "revision": 2, "body": {"verdict": "accepted"}},
    ]}
    html = webapp._trail_html(body)
    assert "moved gaps" in html, "the code correction is not shown"
    assert "code   r2" in html
    # No check line may be rendered with an empty verdict.
    for line in html.split("\n"):
        if line.strip().startswith("check"):
            assert "accepted" in line or "rejected" in line, line


def test_a_spent_daily_quota_is_reported_once_not_silently_absorbed(capsys):
    """The fallback working is the design succeeding - but 29 of 30 real
    reports ran on the slower secondary without a word on screen, which reads
    as "the system got slower", not "the fast provider is out of quota until
    tomorrow". Warn once per model, to stderr, and keep working."""
    from slice import llm
    llm._DEGRADED_WARNED.clear()
    body = ('{"error":{"message":"Rate limit reached for model `x` on tokens '
            'per day (TPD): Limit 200000, Used 198913"}}')
    llm._warn_degraded("qwen/qwen3.8-27b", 884.0, body)
    first = capsys.readouterr().err
    assert "rate limited" in first
    assert "daily token quota" in first, "should name the real cause"
    assert "Falling back" in first

    # Same model again: silent, or a cohort run prints this 30 times.
    llm._warn_degraded("qwen/qwen3.8-27b", 884.0, body)
    assert capsys.readouterr().err == ""

    # A per-minute limit is a queue, not a spent quota - no daily wording.
    llm._DEGRADED_WARNED.clear()
    llm._warn_degraded("other-model", 45.0, '{"error":{"message":"rate limit"}}')
    assert "daily token quota" not in capsys.readouterr().err


def test_moving_an_entry_on_verdict_does_not_duplicate_a_concept():
    """Measured on the real cohort: a draft listed four strengths and two gaps,
    every concept distinct WITHIN its own list, but both gaps naming a concept
    already in strengths. enforce_verdicts() moved them on verdict and appended
    blindly, so the student saw 'knowing when a loop or function stops' twice
    in strengths with the same sentence under both. The move is right; the
    blind append was not."""
    facts = {"by_concept": [
        {"concept": "loops", "asked": 4, "correct": 3, "wrong_answer_count": 1,
         "missed_in_topics": ["A"]}]}
    body = {"headline": "h",
            "strengths": [{"concept": "loops", "verdict": "strong",
                           "evidence": "The one miss checked only at the start."}],
            "gaps": [{"concept": "loops", "verdict": "weak",
                      "evidence": "The one miss checked only at the start."}],
            "next_step": "n", "uncertainty": "u"}

    notes = report.enforce_verdicts(body, facts)
    names = [e["concept"] for e in body["strengths"]]
    assert names.count("loops") == 1, f"concept duplicated: {names}"
    assert not body["gaps"], "the entry should have left gaps"
    assert any("duplicate" in n for n in notes)


def test_a_concept_listed_twice_is_rejected():
    facts = {"by_concept": [
        {"concept": "a", "asked": 3, "correct": 0, "wrong_answer_count": 3,
         "missed_in_topics": ["X", "Y"]}]}
    body = {"headline": "h", "strengths": [],
            "gaps": [{"concept": "a", "verdict": "weak", "evidence": "one"},
                     {"concept": "a", "verdict": "weak", "evidence": "two"}],
            "next_step": "n", "uncertainty": "u"}
    check = report.check_distinct_evidence(body, facts)
    assert check is not None and "listed twice" in check.detail
