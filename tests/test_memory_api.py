"""The memory API's contract, including the one rule that is easy to break later.

The app is shown while a person explains what is happening. If the API ever
starts returning a `why`, a `reason`, or a "this is expected" flag, a screen
will eventually render it and either steal that explanation or contradict it.
That is a product decision, so it gets a test rather than a comment.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest

from app import memory_api


@pytest.fixture()
def demo_db(tmp_path, monkeypatch):
    """A miniature two-sitting identity, in the shape the real builder writes."""
    path = tmp_path / "memory.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE runs (id TEXT PRIMARY KEY, domain TEXT, state TEXT,
                           created_at REAL, updated_at REAL, meta_json TEXT);
        CREATE TABLE versions (run_id TEXT, seq INTEGER, kind TEXT,
                               produced_by TEXT, payload_json TEXT,
                               created_at REAL, PRIMARY KEY (run_id, seq));
    """)

    def add(run_id, sitting, state, records):
        con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)",
                    (run_id, "recall", state, time.time() + sitting,
                     time.time() + sitting,
                     json.dumps({"student_id": "mem_test", "display_name": "Test T.",
                                 "department": "robotics", "sitting": sitting,
                                 "synthetic_timeline": True})))
        for seq, (kind, payload) in enumerate(records, start=1):
            con.execute("INSERT INTO versions VALUES (?,?,?,?,?,?)",
                        (run_id, seq, kind, "test", json.dumps(payload), time.time()))

    attempt = {
        "assignment_id": "diagnostic_sitting_1", "date": "2026-06-08",
        "assignment_prompt": "twenty questions",
        "quiz_meta": {"score": 18, "asked": 20, "replayed_from_real_student": "stu_x",
                      "replayed_from_real_name": "A Real Student"},
    }
    evidence = {"items": [
        {"source_ref": "rb_t2_q4#D", "concept": "measurement", "kind": "difficulty",
         "note": "n", "supported": True},
        {"source_ref": "rb_t1_q1#A", "concept": "position", "kind": "strength",
         "note": None, "supported": True},
    ]}

    add("run_one", 1, "complete", [
        ("attempt", attempt), ("evidence", evidence),
        ("comparison", {"label": "not_enough_evidence", "related_refs": [],
                        "explanation": "first submission"}),
    ])
    add("run_two", 2, "needs_review", [
        ("attempt", {**attempt, "assignment_id": "diagnostic_sitting_2",
                     "date": "2026-06-29"}),
        ("evidence", evidence),
        ("comparison", {"label": "recurring", "related_refs": ["rb_t2_q4#D"],
                        "explanation": "same mistake as sitting 1"}),
        ("finding", {"status": "candidate_recurring", "statement": "s",
                     "uncertainty": "u", "proposed_next_step": "n",
                     "supporting_refs": ["rb_t2_q4#D"]}),
        ("check", {"verdict": "needs_review"}),
    ])
    con.commit()
    con.close()
    monkeypatch.setattr(memory_api, "DB", path)
    return path


def test_sittings_are_oldest_first_and_know_what_they_could_see(demo_db):
    """The persistence itself: sitting 1 sees nothing, sitting 2 sees sitting 1."""
    body = memory_api.student("mem_test")
    assert [s["sitting"] for s in body["sittings"]] == [1, 2]
    assert body["sittings"][0]["prior_sittings_visible"] == 0
    assert body["sittings"][1]["prior_sittings_visible"] == 1


def test_outcome_words_are_the_three_the_app_designs_for(demo_db):
    body = memory_api.student("mem_test")
    assert body["sittings"][0]["outcome"] == "first"
    assert body["sittings"][1]["outcome"] == "found"
    assert {s["outcome"] for s in body["sittings"]} <= {"first", "found", "none_found"}


def test_a_claim_carries_the_answers_it_rests_on(demo_db):
    """A finding next to its citations is checkable; on its own it is an assertion."""
    body = memory_api.sitting("run_two")
    assert body["cited_answers"] == ["rb_t2_q4#D"]
    cited = [a for a in body["answers"] if a["cited_here"]]
    assert [a["ref"] for a in cited] == ["rb_t2_q4#D"]


def test_handing_off_to_a_human_is_visible(demo_db):
    body = memory_api.student("mem_test")
    assert body["sittings"][1]["awaiting_human"] is True
    assert body["summary"]["awaiting_human"] == 1


def test_provenance_travels_with_every_record(demo_db):
    """The app must never be able to show this data without the disclosure."""
    for body in (memory_api.students(), memory_api.student("mem_test"),
                 memory_api.sitting("run_two")):
        assert body["disclosure"]
        assert "real answer from a real student" in body["disclosure"]
    assert memory_api.sitting("run_two")["real_answers_from"] == "A Real Student"


def test_the_api_never_explains_why():
    """The presenter explains why. The API states what.

    Guarding the field names rather than the prose, because a `reason` field is
    how the explanation would get into the UI by accident.
    """
    source = (memory_api.__file__)
    forbidden = ('"why"', '"reason"', '"expected"', '"is_expected"',
                 '"cause"', '"diagnosis"')
    text = open(source).read()
    for key in forbidden:
        assert key not in text, f"{key} would put an explanation on screen"


def test_missing_database_says_how_to_build_it(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_api, "DB", tmp_path / "absent.db")
    with pytest.raises(Exception) as e:
        memory_api.students()
    assert "build_memory_demo" in str(e.value)
