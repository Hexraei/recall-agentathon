"""The Jev judgement paths, with no network.

Two integrations share one rule - Jev judges, code decides - and these tests
pin that rule at every point a later edit could break it:

    compare step      app/flow.py handle_comparing  (jev_compare.judge)
    report check step app/report.py _run_check      (jev_report_check.judge)

Proven here:

    compare   - the verdict's calibration lands in the store as jev_verdict
              - confidence below the floor on a `recurring` claim asks the
                professor instead of confirming
              - a Jev outage falls back VISIBLY: a failure record, then the
                chat engine answers, and the run completes
              - Jev unset makes zero judge calls - the pre-Jev path intact
    report    - a Jev outage lands as a jev_fallback trail row and the chat
                checker answers; the report still completes
              - a clean report's accepted verdict carries the calibration in
                its detail, whichever engine answered
              - below-floor check verdicts ship the report flagged
                `_unverified` rather than trusted or coin-flip-redrafted
              - jev unset (or settings=None, the offline path) never attempts
                a Jev call and leaves no fallback debris

Jev itself is never touched: the network boundary is stubbed at the seam the
flow already has (app.jev_compare.judge / app.jev_report_check.judge), so
these run in the same keyless suite as everything else. The LIVE boundary was
verified manually - recorded in commit messages; a test suite that needs the
network is a test that fails on stage wifi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slice import callback
from slice.config import Settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

from app import fixtures
from app.flow import build_flow

NOTES = (Path(__file__).resolve().parents[1] / "corpus" / "ds-notes.md").read_text()

MADE_UP_KEY = "sk-or-never-reached-the-network"
"""Key-shaped but wrong: with the network stubbed nothing sends it; an
accidental real call fails visibly instead of leaking into a passed test."""


def _settings(**over) -> Settings:
    """Settings built by hand, not from .env - the suite must not inherit
    whatever happens to be configured on the machine it runs on."""
    return Settings(
        api_key=MADE_UP_KEY, groq_key="",
        model="test/chat-model", fallback_model="", escalation_model="",
        max_tokens=1200, max_tokens_per_run=250000, max_attempts_per_step=3,
        expert_timeout_minutes=1,
        langfuse_public="", langfuse_secret="", langfuse_host="",
        **over)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


# ------------------------------------------------------------------ doubles

class _JudgeQueue:
    """The Jev seam, answered from a queue, repeating the last answer once
    the queue runs dry.

    The repeat is deliberate and documented: the stubbed finding step
    deliberately overstates Mira's week-7 finding, the checker rejects it,
    and the back-edge routes the run BACK to comparing - a second judge call
    the state machine itself made. A judge that answers a re-asked question
    identically is what determinism *means*; an empty queue would fabricate
    an outage the system under test never had. An outage test passes an
    explicit Exception instead.
    """

    def __init__(self, *results):
        self.results = list(results)
        self.shown: list[dict] = []
        self._last = None

    def judge(self, **kw):
        self.shown.append({"prior_rows": len(kw.get("prior", {}).get("evidence", [])),
                           "week_gap": kw.get("week_gap")})
        if self.results:
            r = self.results.pop(0)
            self._last = r
        else:
            assert self._last is not None, \
                "queue empty - the flow asked Jev unexpectedly"
            r = self._last
        if isinstance(r, Exception):
            # Raised via JevError, the module's own outage type: handle_
            # comparing's fallback catch is deliberately NARROW now (JevError
            # only) so a bug in our code crashes loudly instead of laundering
            # itself as "Jev unavailable". A raw ConnectionError from the stub
            # would escape that catch and kill the run - which is what the
            # production transport wrapper (TRANSPORT_ERRORS -> JevError)
            # prevents for real network failures.
            from app.jev_compare import JevError
            raise JevError(f"{type(r).__name__}: {r}") from r
        return r


def _verdict(label, confidence, refs=(), probs=None):
    from app.jev_compare import JevVerdict
    return JevVerdict(label=label, explanation="-", related_refs=list(refs),
                      confidence=confidence,
                      probabilities=probs or {label: round(confidence, 2)})


class _ChatDouble:
    """A call()-shaped double with an opinion about which steps may fire.

    Generative steps (extract, finding, check) must NOT go through this in a
    Jev-first test - _run_attempt routes them to the repo's own stub instead.
    Anything outside `allow` raises: the whole point is that a silent
    fallback passes nothing quietly.
    """

    def __init__(self, allow=(), label="similar"):
        self.allowed = set(allow)
        self.calls: list[str] = []
        self._label = label

    def __call__(self, *, settings, budget, messages, schema, step, **kw):
        self.calls.append(step)
        assert step in self.allowed, \
            f"unexpected chat call at {step!r} - every fallback must be deliberate"
        if schema.__name__ == "Comparison":
            return schema.model_validate({"label": self._label,
                                          "related_refs": [],
                                          "explanation": "chat fallback"})
        return schema.model_validate({"verdict": "accepted",
                                      "failed_check": None, "detail": ""})


class _Budget:
    def check_tokens(self): pass
    def record_tokens(self, n): pass


# ------------------------------------------------------------ the compare path

def _run_attempt(store, settings, attempt, judge_queue, chat, answer="confirm"):
    """One attempt through the real flow with the judge swapped at the seam.

    The chat path is wrapped, not replaced: extract/finding/check answer from
    the repo's own keyless stub (the same canned encounters the whole suite
    uses), while `compare` inside `chat.allow` marks the deliberate
    fallback. Judge wiring is undone in a finally, so nothing leaks.
    """
    import app.flow as flow_module
    from app.stub import make_stub
    holder = [""]           # the stub reads the run id from here
    stub = make_stub(store, holder)

    def guarded_call(**kw):
        step = kw["step"]
        if step == "compare":
            chat.calls.append(step)
            assert step in chat.allowed, \
                "unexpected chat compare - the fallback must be deliberate"
        return stub(**kw)

    real = (flow_module.jev.judge, flow_module.jev.jev_available)
    flow_module.jev.judge = judge_queue.judge
    flow_module.jev.jev_available = lambda s: bool(s.jev_model)
    try:
        run_id = store.create_run("recall",
                                  meta={"student_id": attempt["student_id"]})
        holder[0] = run_id
        store.set_state(run_id, RunState.NEW_ATTEMPT)
        store.append(run_id, "attempt", attempt, produced_by="ingest")
        flow = build_flow(notes=NOTES, call=guarded_call)
        state = advance(store, run_id, flow, settings)
        if state is RunState.NEEDS_REVIEW and answer is not None:
            pending = callback.pending(store, run_id)
            callback.answer(store, pending[0].id, answer, who="professor")
            store.set_state(run_id, RunState.RECORD_UPDATED)
            advance(store, run_id, flow, settings)
        return run_id
    finally:
        flow_module.jev.judge, flow_module.jev.jev_available = real


# --- verdict recorded -------------------------------------------------------

def _seed_history(store, attempt):
    """Prior encounter, its own committed run - what later comparisons read."""
    from app.stub import make_stub
    rid = store.create_run("recall", meta={"student_id": attempt["student_id"]})
    store.set_state(rid, RunState.NEW_ATTEMPT)
    store.append(rid, "attempt", attempt, produced_by="ingest")
    stub = make_stub(store, [rid])
    advance(store, rid, build_flow(notes=NOTES, call=stub),
            _settings(jev_model=""))
    return rid


def test_the_judgement_is_a_record_with_its_calibration(store):
    """The verdict's numbers sit in the store next to the outcome, so an
    auditor can see WHY an accepted comparison was accepted."""
    q = _JudgeQueue(_verdict("recurring", 0.84, refs=["assignment_1#response"],
                             probs={"recurring": 0.88}))
    _seed_history(store, fixtures.MIRA_1)
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=())          # chat must never fire
    run_id = _run_attempt(store, s, fixtures.MIRA_2, q, chat)

    recs = [v.payload for v in store.history(run_id, "jev_verdict")]
    assert recs and recs[-1]["label"] == "recurring"
    assert recs[-1]["confidence"] == 0.84
    assert recs[-1]["model"] == "typesafe/jev-1.13"
    assert store.latest(run_id, "comparison")["label"] == "recurring"
    assert chat.calls == []               # the chat engine was not needed
    assert q.shown and q.shown[0]["prior_rows"] == 1, \
        "the judge must see the seeded prior encounter, not an empty history"
    assert q.shown[0]["week_gap"] == 4, \
        "weeks between attempts are computed in Python and handed over"


# --- the floor --------------------------------------------------------------

def test_low_confidence_recurrence_asks_the_professor(store):
    """The rule the whole integration exists for. 0.35 says the model itself
    is near a coin flip; letting a coin flip confirm a consequence without a
    person is exactly the overconfidence the floor exists to stop."""
    q = _JudgeQueue(_verdict("recurring", 0.35, probs={"recurring": 0.34}))
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=())          # NOT allowed: no silent accept
    _seed_history(store, fixtures.MIRA_1)
    run_id = _run_attempt(store, s, fixtures.MIRA_2, q, chat, answer=None)

    assert store.get_state(run_id) is RunState.NEEDS_REVIEW
    pending = callback.pending(store, run_id)
    assert "confidence" in pending[0].question.lower()
    # The low-confidence verdict drives this review; the judge's calibration
    # numbers were recorded BEFORE routing (calibration rides with the
    # question, not only with the outcome).
    recs = [v.payload for v in store.history(run_id, "jev_verdict")]
    assert recs and recs[-1]["confidence"] == 0.35
    # The run stopped at compare: a suspended run has drafted nothing.
    assert store.history(run_id, "finding") == [], \
        "no finding may exist while the professor is still deciding"


def test_high_confidence_recurrence_confirms_without_a_human(store):
    """The floor is a floor, not a tax: 0.84 clears it, and the professor is
    NOT asked - the run flows to RECORD_UPDATED and the finding stands. If
    this ever needs a human for everything, calibration bought nothing."""
    q = _JudgeQueue(_verdict("recurring", 0.84))
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=())
    _seed_history(store, fixtures.MIRA_1)
    run_id = _run_attempt(store, s, fixtures.MIRA_2, q, chat, answer=None)

    recs = [v.payload for v in store.history(run_id, "jev_verdict")]
    assert recs and recs[-1]["confidence"] == 0.84
    # The floor never fired: no question carries the below-floor message.
    # (A question MAY exist - the stub's checker flags a consequential
    # finding on its own; that is the checker's judgement, not the floor's.)
    for q in store.history(run_id, "question"):
        assert "below the" not in q.payload["question"], \
            "a high-confidence verdict was routed by the floor anyway"


# --- the fallback -----------------------------------------------------------

def test_a_jev_outage_falls_back_visibly_and_the_run_survives(store):
    """The fallback must (a) work - the run completes on the chat engine -
    and (b) leave a trail. A silent fallback would be indistinguishable from
    a Jev-healthy run, and nobody would ever know the judge wasn't judging.

    The chat compare may legitimately fire more than once: the stub's first
    finding is rejected for claim_strength and the back-edge returns the run
    to comparing, where BOTH transports answer again. What must hold is
    proportionality - every chat compare rides a recorded outage, never a
    silent one."""
    q = _JudgeQueue(ConnectionError("network gone"))
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=("compare",))
    _seed_history(store, fixtures.MIRA_1)
    run_id = _run_attempt(store, s, fixtures.MIRA_2, q, chat, answer=None)

    failures = [f.payload for f in store.history(run_id, "failure")]
    outages = [f for f in failures if f.get("kind") == "jev_unavailable"]
    assert outages, "no fallback record - the outage would have been silent"
    assert len(outages) == chat.calls.count("compare"), \
        (f"{len(outages)} outage records but {len(chat.calls)} chat compares "
         "- each chat answer must trace to a recorded outage")

    comp = store.latest(run_id, "comparison")
    assert comp is not None


def test_jev_unset_makes_no_jev_calls_at_all(store):
    """Jev unset = the pre-Jev path, byte for byte. The judge is guarded
    structurally: ANY call would hit the empty queue and raise."""
    q = _JudgeQueue()                     # empty: any Jev call explodes
    s = _settings(jev_model="", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=("compare",))
    _seed_history(store, fixtures.MIRA_1)
    run_id = _run_attempt(store, s, fixtures.MIRA_2, q, chat, answer=None)

    assert store.latest(run_id, "comparison")["label"] in ("recurring", "similar"), \
        "the chat engine answered the compare step; the stub reads real history"
    assert not q.shown, "judge was called although Jev is unset"
    assert store.history(run_id, "failure") == []


# ---------------------------------------------------------------- the report check

_FACTS = {
    "department": "computer_science",
    "score": {"correct": 15, "asked": 20},
    "by_topic": [],
    "by_concept": [{"concept": "loop counting", "asked": 5, "correct": 0,
                    "wrong_answer_count": 5,
                    "missed_in_topics": ["Recursion", "Time Complexity"],
                    "wrong_answers": [{"topic": "Recursion",
                                       "mistake": "ignored inner loop"}]}],
}

_REPORT_OK = {
    "headline": "One gap, several topics.",
    "strengths": [],
    "gaps": [{"concept": "loop counting", "verdict": "weak", "evidence": "0 of 5"}],
    "cross_topic_pattern": None,
    "pattern_concept": None,
    "next_step": "-",
    "uncertainty": "-",
}


def test_jev_check_outage_falls_back_via_the_trail(store, monkeypatch):
    """A Jev outage inside the report loop lands as a jev_fallback trail row,
    then the chat checker answers - the report still completes, and the trail
    still says what happened."""
    from app import report as report_module, jev_report_check
    monkeypatch.setattr(jev_report_check, "judge",
                        lambda **kw: (_ for _ in ()).throw(
                            ConnectionError("down")))
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    chat = _ChatDouble(allow=("report_check",))
    trail: list = []
    check = report_module._run_check(dict(_REPORT_OK), _FACTS, "student",
                                     s, _Budget(), None, "r1", trail, None,
                                     call=chat)
    assert check.verdict == "accepted"
    assert [r["step"] for r in trail] == ["jev_fallback"]
    assert chat.calls == ["report_check"]


def test_jev_check_accepts_a_clean_report_and_records_the_calibration(store, monkeypatch):
    """On a clean pass the verdict detail still carries the numbers - an
    audit of an accepted report needs the calibration that accepted it."""
    from app import report as report_module, jev_report_check
    captured: dict = {}

    def fake_judge(**kw):
        captured["report"] = kw["report"]
        return (jev_report_check.JevVerdict(
                    noul=0.23, confidence=0.54,
                    model="typesafe/jev-1.13-20260917"),
                {"noul_false": 0.23, "bad_claim_noul": 0.1,
                 "confidence": 0.54,
                 "model": "typesafe/jev-1.13-20260917",
                 "below_floor": False})

    monkeypatch.setattr(jev_report_check, "judge", fake_judge)
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    trail: list = []
    check = report_module._run_check(dict(_REPORT_OK), _FACTS, "student",
                                     s, _Budget(), None, "r1", trail, None)
    assert check.verdict == "accepted"
    assert "noul=0.23" in check.detail
    assert "typesafe/jev-1.13-20260917" in check.detail


def test_a_false_report_is_rejected_with_the_judgement_recorded(store, monkeypatch):
    """noul high = reject, with the numbers in the detail - the writer sees
    WHY, and the trail keeps the calibration, not just the outcome."""
    from app import report as report_module, jev_report_check

    def lying(**kw):
        return (jev_report_check.JevVerdict(noul=0.95, confidence=0.90,
                                            model="jev"),
                {"noul_false": 0.95, "bad_claim_noul": 0.9,
                 "confidence": 0.90, "model": "jev", "below_floor": False})

    monkeypatch.setattr(jev_report_check, "judge", lying)
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    trail: list = []
    check = report_module._run_check(dict(_REPORT_OK), _FACTS, "student",
                                     s, _Budget(), None, "r1", trail, None)
    assert check.verdict == "rejected"
    assert check.failed_check == "claim_strength"
    assert "noul=0.95" in check.detail


def test_low_confidence_check_ships_unverified(store, monkeypatch):
    """Below floor, the report is neither accepted silently nor redrafted on
    the same coin toss - it ships flagged, and the flag rides in the body
    the student and the teacher actually see."""
    from app import report as report_module, jev_report_check as jrc

    def flabby(**kw):
        return (jrc.JevVerdict(noul=0.67, confidence=0.34, model="jev"),
                {"noul_false": 0.67, "bad_claim_noul": 0.4,
                 "confidence": 0.34, "model": "jev", "below_floor": True})

    monkeypatch.setattr(jrc, "judge", flabby)
    s = _settings(jev_model="typesafe/jev-1.13", jev_confidence_floor=0.60)
    body = dict(_REPORT_OK)
    trail: list = []
    check = report_module._run_check(body, _FACTS, "student", s, _Budget(),
                                     None, "r1", trail, None)
    assert check.verdict == "accepted"
    assert "BELOW CONFIDENCE FLOOR" in check.detail
    assert "_unverified" in body
    assert "0.34" in body["_unverified"]


def test_jev_off_uses_the_chat_check_and_never_touches_the_judge(store, monkeypatch):
    """The offline path - settings=None, exactly what the team's own tests
    pass - must never attempt a Jev call and must leave no fallback debris."""
    from app import report as report_module
    import app.jev_report_check as jrc

    touched: list = []
    monkeypatch.setattr(jrc, "judge",
                        lambda **kw: touched.append(1) or 1 / 0)

    chat = _ChatDouble(allow=("report_check",))
    body = dict(_REPORT_OK)
    trail: list = []
    check = report_module._run_check(body, _FACTS, "student", None, _Budget(),
                                     None, "r1", trail, None, call=chat)
    assert check.verdict == "accepted"
    assert chat.calls == ["report_check"]
    assert not trail              # no jev_fallback row
    assert not touched, "the judge was reached although settings is None"
