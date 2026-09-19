"""Tests for the quiz app: the bank's shape, the roster's counting, and the
report agent's two gates.

The counting tests matter more than they look. The report agent is TOLD the
counts and asked only to interpret them - so if roster.by_concept miscounts,
the model will interpret a wrong number with complete confidence and nothing
downstream will catch it. These tests are the only thing standing there.
"""
from __future__ import annotations

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


def test_every_wrong_option_names_a_misconception_and_no_right_one_does():
    """The misconception mapping IS the diagnosis - a wrong option without one
    is a question that teaches the report nothing."""
    for q in bank.ALL:
        for o in q.options:
            assert (o.misconception is None) == o.correct, (q.id, o.key)


def test_concepts_span_more_than_one_topic():
    """The whole cross-topic story depends on this. If every concept sat in a
    single topic, 'one cause behind three topics' could never be true and the
    report would have nothing to find."""
    for dept in bank.DEPARTMENTS:
        spanning = {}
        for q in bank.for_department(dept):
            spanning.setdefault(q.concept, set()).add(q.topic)
        multi = [c for c, t in spanning.items() if len(t) > 1]
        assert len(multi) >= 3, (dept, spanning)


# --------------------------------------------------------------- the roster

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
                wrong_concepts={"counting work inside loops"})

    rows = {r["concept"]: r for r in roster.by_concept(store, sid)}
    loops = rows["counting work inside loops"]
    assert loops["correct"] == 0
    assert loops["asked"] == 5
    # The point of the whole design: one concept, several topics.
    assert len(loops["topics"]) >= 3, loops["topics"]


def test_score_and_topic_counts_agree(store):
    sid = roster.create_student(store, "A", "1", "R", "robotics")
    _answer_all(store, sid, "robotics",
                wrong_concepts={"reasoning about singularities and degeneracy"})
    got, asked = roster.score(store, sid)
    assert asked == 20
    assert got == 17          # 3 questions carry that concept
    assert sum(t["asked"] for t in roster.by_topic(store, sid)) == 20
    assert sum(t["correct"] for t in roster.by_topic(store, sid)) == got


def test_class_common_wrong_counts_students_converging_on_one_option(store):
    """A shared misconception is students landing on the SAME wrong option.
    That count is what separates a teaching problem from a tutoring one."""
    for i in range(3):
        sid = roster.create_student(store, f"S{i}", "1", f"R{i}", "computer_science")
        _answer_all(store, sid, "computer_science",
                    wrong_concepts={"counting work inside loops"})

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
                     {"concept": "refs", "verdict": "strong", "evidence": "y"}]}

    fixed = report.enforce_verdicts(body, facts)

    assert body["gaps"][0]["verdict"] == "strong"   # 4 of 5
    assert body["gaps"][1]["verdict"] == "weak"     # 0 of 3
    assert len(fixed) == 2
    assert "loops" in fixed[0] and "4 of 5" in fixed[0]


def test_verdict_correction_reads_class_counts_too(store):
    """class_by_concept spells the total `answered`; by_concept spells it
    `asked`. One rule reads both, so both must carry the same key or the rule
    silently applies to half its inputs."""
    for i in range(3):
        sid = roster.create_student(store, f"S{i}", "1", f"R{i}", "computer_science")
        _answer_all(store, sid, "computer_science",
                    wrong_concepts={"counting work inside loops"})
    rows = roster.class_by_concept(store, "computer_science")
    assert all("asked" in r for r in rows)
    assert all(r["asked"] == r["answered"] for r in rows)

    facts = {"by_concept": rows}
    body = {"teach_again": [{"concept": "counting work inside loops",
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


_FACTS_STUDENT = {
    "department": "computer_science",
    "score": {"correct": 15, "asked": 20},
    "by_topic": [], "wrong_answers": [],
    "by_concept": [{"concept": "counting work inside loops", "asked": 5,
                    "correct": 0, "topics": ["Recursion", "Time Complexity"]}],
    "class_average_by_concept": [], "class_size": 1,
}

_OK_REPORT = {
    "headline": "One gap, several topics.",
    "strengths": [], "gaps": [{"concept": "counting work inside loops",
                               "verdict": "weak", "evidence": "0 of 5"}],
    "cross_topic_pattern": "Same cause in Recursion and Time Complexity.",
    "next_step": "Trace nested loops by hand.",
    "uncertainty": "Twenty multiple-choice questions cannot show reasoning.",
}


def test_an_accepted_draft_stops_the_loop(store):
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={"counting work inside loops"})
    call = _Scripted(_OK_REPORT, {"verdict": "accepted"})

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == 1
    assert call.calls == ["student_report", "report_check"]
    assert "_unverified" not in body


def test_a_rejection_sends_the_draft_back_with_the_reason(store):
    """The back-edge. The second request must carry the objection - a blind
    retry of an identical prompt usually fails identically."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={"counting work inside loops"})

    overclaim = dict(_OK_REPORT, cross_topic_pattern="Everything is connected.")
    call = _Scripted(overclaim,
                     {"verdict": "rejected", "failed_check": "claim_strength",
                      "detail": "The pattern is not traceable to specific rows."},
                     _OK_REPORT, {"verdict": "accepted"})

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == 2
    assert body["_trail"][0]["step"] == "draft"
    assert body["_trail"][1]["body"]["verdict"] == "rejected"
    assert body["_trail"][2]["step"] == "draft"


def test_the_rejection_detail_reaches_the_next_prompt(store):
    reason = "The pattern is not traceable to specific rows."
    msgs = report.build_student_messages(
        _FACTS_STUDENT,
        {"report": _OK_REPORT, "failed_check": "claim_strength", "detail": reason})
    text = msgs[-1]["content"]
    assert "REJECTED" in text
    assert reason in text


def test_a_report_that_never_passes_ships_flagged_not_silently(store):
    """Three rejections spends the budget. The last draft still goes out -
    a teacher is better served by a flagged report than by nothing - but it
    must not look like it passed."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science")
    reject = {"verdict": "rejected", "failed_check": "claim_strength",
              "detail": "still overclaims"}
    call = _Scripted(_OK_REPORT, reject, _OK_REPORT, reject, _OK_REPORT, reject)

    body = report.for_student(store, sid, settings=None, call=call, force=True)
    assert body["_revisions"] == report.MAX_DRAFTS
    assert body["_unverified"] == "still overclaims"
    assert not call.replies, "the loop stopped early"


def test_a_slow_report_stops_at_the_deadline_and_ships_what_it_has(store, monkeypatch):
    """The wall-clock fence. During a network drop one report stacked
    per-request timeouts to ~40 minutes; no per-call timeout was wrong, they
    simply composed. MAX_DRAFTS cannot catch that because the time goes INSIDE
    one draft's call chain, so the deadline is a third, separate counter."""
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science")

    reject = {"verdict": "rejected", "failed_check": "claim_strength",
              "detail": "overclaims"}
    call = _Scripted(_OK_REPORT, reject, _OK_REPORT, reject, _OK_REPORT, reject)

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
    assert body["headline"] == _OK_REPORT["headline"]
    assert len(call.replies) == 4, "should have stopped after the first pair"


def test_a_cached_report_does_not_call_the_model_again(store):
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science")
    call = _Scripted(_OK_REPORT, {"verdict": "accepted"})
    report.for_student(store, sid, settings=None, call=call, force=True)

    def _blow_up(**kw):
        raise AssertionError("cached report still called the model")

    again = report.for_student(store, sid, settings=None, call=_blow_up)
    assert again["headline"] == _OK_REPORT["headline"]


def test_the_facts_handed_to_the_model_come_from_sql_not_the_model(store):
    """The model interprets counts; it never produces them. If this ever
    inverts, a miscount becomes a confident diagnosis with nothing to catch it.
    """
    sid = roster.create_student(store, "A", "1", "R", "computer_science")
    _answer_all(store, sid, "computer_science",
                wrong_concepts={"counting work inside loops"})
    facts = report.student_facts(store, sid)
    assert facts["score"] == {"correct": 15, "asked": 20}
    loops = next(r for r in facts["by_concept"]
                 if r["concept"] == "counting work inside loops")
    assert loops == {"concept": "counting work inside loops", "asked": 5,
                     "correct": 0, "topics": loops["topics"]}
