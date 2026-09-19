"""Who took the quiz, and what they answered.

Two tables alongside the kit's append-only `versions` table, in the same file.
They are separate because they answer a different question: `versions` is the
audit trail of one agent run, this is the roster the agent runs OVER. Mixing
them would mean a student's identity only existing inside whichever run last
touched it.

Responses are insert-only by convention and by the UNIQUE constraint - a student
answers each question once. That is what makes "how did the class do on
cs_t3_q1" a straight count rather than a guess about which row is current.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from slice.store import Store

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL,
    register_no TEXT NOT NULL,
    department  TEXT NOT NULL,
    created_at  REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS students_reg ON students(register_no);

CREATE TABLE IF NOT EXISTS responses (
    student_id   TEXT NOT NULL REFERENCES students(id),
    question_id  TEXT NOT NULL,
    department   TEXT NOT NULL,
    topic        TEXT NOT NULL,
    concept      TEXT NOT NULL,
    chosen       TEXT NOT NULL,
    correct      INTEGER NOT NULL,
    misconception TEXT,
    seconds      REAL NOT NULL DEFAULT 0,
    answered_at  REAL NOT NULL,
    PRIMARY KEY (student_id, question_id)
);
CREATE INDEX IF NOT EXISTS responses_by_dept ON responses(department, question_id);

-- The report the agent produced, cached so reopening the page is free and so a
-- teacher and a student see the SAME text rather than two independent runs.
CREATE TABLE IF NOT EXISTS reports (
    scope      TEXT NOT NULL,   -- 'student' | 'class'
    key        TEXT NOT NULL,   -- student id, or department
    run_id     TEXT,
    body_json  TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (scope, key)
);
"""


def init(store: Store) -> None:
    store.db.executescript(SCHEMA)


# ------------------------------------------------------------------- students

def create_student(store: Store, name: str, phone: str, register_no: str,
                   department: str) -> str:
    """Register a student, or return the existing id for a known register number.

    Returning the existing id rather than erroring is deliberate: a tester who
    refreshes the signup page mid-demo should land back in their own quiz, not
    hit a wall in front of an audience.
    """
    row = store.db.execute(
        "SELECT id FROM students WHERE register_no=?", (register_no,)
    ).fetchone()
    if row:
        return row["id"]
    sid = f"stu_{uuid.uuid4().hex[:10]}"
    store.db.execute(
        "INSERT INTO students(id, name, phone, register_no, department, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (sid, name, phone, register_no, department, time.time()),
    )
    return sid


def student(store: Store, student_id: str) -> dict[str, Any] | None:
    row = store.db.execute(
        "SELECT * FROM students WHERE id=?", (student_id,)
    ).fetchone()
    return dict(row) if row else None


def students_in(store: Store, department: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT * FROM students WHERE department=? ORDER BY name", (department,)
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ responses

def record(store: Store, student_id: str, question, chosen: str,
           seconds: float = 0.0) -> None:
    """Store one answer. No model call, no feedback - see app/report.py for why."""
    opt = question.option(chosen)
    store.db.execute(
        "INSERT OR IGNORE INTO responses(student_id, question_id, department,"
        " topic, concept, chosen, correct, misconception, seconds, answered_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (student_id, question.id, question.department, question.topic,
         question.concept, chosen, int(opt.correct), opt.misconception,
         seconds, time.time()),
    )


def answers(store: Store, student_id: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT * FROM responses WHERE student_id=? ORDER BY answered_at",
        (student_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def answered_ids(store: Store, student_id: str) -> set[str]:
    return {r["question_id"] for r in store.db.execute(
        "SELECT question_id FROM responses WHERE student_id=?", (student_id,))}


# -------------------------------------------------------------- aggregate view
# Plain SQL, no model. The agent reasons about these numbers; it does not
# compute them. A model asked to both count and interpret will occasionally
# miscount, and then interpret its own bad count with total confidence.

def by_topic(store: Store, student_id: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT topic, COUNT(*) n, SUM(correct) got FROM responses"
        " WHERE student_id=? GROUP BY topic ORDER BY topic", (student_id,)
    ).fetchall()
    return [{"topic": r["topic"], "asked": r["n"], "correct": r["got"]} for r in rows]


def by_concept(store: Store, student_id: str) -> list[dict[str, Any]]:
    """The cross-topic view - the one that makes the report worth reading.

    Concepts deliberately span topics in app/bank.py, so a student missing
    "counting work inside loops" in three different topics shows up here as one
    line, not three unrelated low scores.
    """
    rows = store.db.execute(
        "SELECT concept, COUNT(*) n, SUM(correct) got FROM responses"
        " WHERE student_id=? GROUP BY concept ORDER BY (1.0*SUM(correct)/COUNT(*))",
        (student_id,)
    ).fetchall()
    return [{"concept": r["concept"], "asked": r["n"], "correct": r["got"],
             "topics": _topics_for(store, student_id, r["concept"])}
            for r in rows]


def _topics_for(store: Store, student_id: str, concept: str) -> list[str]:
    return [r["topic"] for r in store.db.execute(
        "SELECT DISTINCT topic FROM responses WHERE student_id=? AND concept=?"
        " AND correct=0", (student_id, concept))]


def misconceptions(store: Store, student_id: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT question_id, topic, concept, misconception FROM responses"
        " WHERE student_id=? AND correct=0 AND misconception IS NOT NULL"
        " ORDER BY concept", (student_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def score(store: Store, student_id: str) -> tuple[int, int]:
    row = store.db.execute(
        "SELECT COUNT(*) n, SUM(correct) got FROM responses WHERE student_id=?",
        (student_id,)
    ).fetchone()
    return int(row["got"] or 0), int(row["n"] or 0)


# ------------------------------------------------------------------ class view

def class_by_question(store: Store, department: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT question_id, topic, concept, COUNT(*) n, SUM(correct) got"
        " FROM responses WHERE department=? GROUP BY question_id"
        " ORDER BY (1.0*SUM(correct)/COUNT(*))", (department,)
    ).fetchall()
    return [{"question_id": r["question_id"], "topic": r["topic"],
             "concept": r["concept"], "answered": r["n"], "correct": r["got"]}
            for r in rows]


def class_by_concept(store: Store, department: str) -> list[dict[str, Any]]:
    """`asked` is spelled the same here as in by_concept() on purpose - the
    verdict rule in app/report.py reads both, and two names for one number is
    how a rule ends up silently applying to only half its inputs."""
    rows = store.db.execute(
        "SELECT concept, COUNT(*) n, SUM(correct) got FROM responses"
        " WHERE department=? GROUP BY concept"
        " ORDER BY (1.0*SUM(correct)/COUNT(*))", (department,)
    ).fetchall()
    return [{"concept": r["concept"], "answered": r["n"], "asked": r["n"],
             "correct": r["got"]} for r in rows]


def class_by_topic(store: Store, department: str) -> list[dict[str, Any]]:
    rows = store.db.execute(
        "SELECT topic, COUNT(*) n, SUM(correct) got FROM responses"
        " WHERE department=? GROUP BY topic ORDER BY topic", (department,)
    ).fetchall()
    return [{"topic": r["topic"], "answered": r["n"], "correct": r["got"]}
            for r in rows]


def class_common_wrong(store: Store, department: str, limit: int = 8) -> list[dict[str, Any]]:
    """The wrong answers most students converged on.

    A misconception twelve students share is a teaching problem; the same
    misconception in one student is a tutoring problem. The teacher report has
    to be able to tell those apart, so the count comes from here.
    """
    rows = store.db.execute(
        "SELECT question_id, topic, concept, chosen, misconception, COUNT(*) n"
        " FROM responses WHERE department=? AND correct=0 AND misconception IS NOT NULL"
        " GROUP BY question_id, chosen ORDER BY n DESC LIMIT ?",
        (department, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def class_size(store: Store, department: str) -> int:
    row = store.db.execute(
        "SELECT COUNT(DISTINCT student_id) n FROM responses WHERE department=?",
        (department,)
    ).fetchone()
    return int(row["n"] or 0)


# --------------------------------------------------------------------- reports

def save_report(store: Store, scope: str, key: str, body: dict, run_id: str | None) -> None:
    store.db.execute(
        "INSERT INTO reports(scope, key, run_id, body_json, created_at)"
        " VALUES (?,?,?,?,?) ON CONFLICT(scope, key) DO UPDATE SET"
        " run_id=excluded.run_id, body_json=excluded.body_json,"
        " created_at=excluded.created_at",
        (scope, key, run_id, json.dumps(body), time.time()),
    )


def load_report(store: Store, scope: str, key: str) -> dict | None:
    row = store.db.execute(
        "SELECT body_json, run_id FROM reports WHERE scope=? AND key=?", (scope, key)
    ).fetchone()
    if not row:
        return None
    body = json.loads(row["body_json"])
    body["_run_id"] = row["run_id"]
    return body
