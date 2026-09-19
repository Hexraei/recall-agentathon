"""Build the longitudinal-memory demo database from real quiz data.

WHAT IS REAL AND WHAT IS NOT, because this is the whole point:

  * REAL   - every answer. Each sitting below is one actual student's actual
             twenty answers, copied unchanged out of the live webapp.db:
             the option they picked, whether it was right, and the
             misconception their wrong option maps to.
  * FAKE   - only the timeline. Four different real students are relabelled
             as one person sitting the same quiz four times, one week apart.

We need that because the system exists to notice the SAME person repeating a
mistake on a SEPARATE occasion, and nobody sits a diagnostic quiz four times
in a 48-hour hackathon. Rather than invent answers, we borrow real ones and
fabricate only the calendar - and we say so out loud in the demo.

app/history.py's _runs_for() matches on runs.meta_json.student_id and orders by
created_at. It has no opinion about where the underlying rows came from, so
replaying real answers under a synthetic student id exercises the genuine
detection path on genuine data.

Two kinds of group are built on purpose:

  Category A - members picked because their wrong answers really do cluster on
               one concept. The system should find the recurrence.
  Category B - members picked because their wrong answers scatter with no
               shared concept. The system should NOT claim a recurrence. That
               is a pass, not a failure: refusing to overclaim is the point.
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slice.records import RunState  # noqa: E402
from slice.store import Store  # noqa: E402

SOURCE_DB = ROOT / "webapp.db"
TARGET_DB = ROOT / "memory.db"

MAX_EVIDENCE = 8
"""app/schema.py caps an EvidenceSet at 8 items and a sitting has 20 answers,
so a sitting must choose. Wrong answers come first - a difficulty is what the
comparison step reasons over - and correct ones fill any space left, so a
strong sitting is not represented as a blank."""

FIRST_SITTING = date(2026, 6, 8)
WEEKS_BETWEEN = 3
"""Three weeks apart, so the fabricated dates read like a term's worth of
coursework rather than four quizzes in a fortnight."""


# --------------------------------------------------------------- the groups
#
# Chosen by inspecting each real student's by_concept/misconceptions rows
# directly, NOT their generated report - docs/evidence/bug-04 records that 59%
# of generated reports drop a real strength or gap from the structured fields,
# so a report's `gaps` list is not trustworthy for this selection.
#
# Category B is selected on a STRICTER rule than "different concepts", and the
# first version of this file got it wrong. Grouping four students whose wrong
# answers merely spread across five concepts still let two of them pick the
# IDENTICAL wrong option on cs_t1_q1 - the same question, the same distractor,
# the same misconception. The comparison step read that as recurrence and, by
# its own stated test ("would one explanation fix both?"), it was right; the
# group label was what was wrong. A negative control has to contain no
# recurrence to find, so members are now required to share no wrong QUESTION at
# all, let alone the same wrong option. In computer science exactly one group
# of four in the whole cohort satisfies that.

GROUPS = [
    {
        "id": "mem_robotics_a",
        "display": "Priya R.",
        "department": "robotics",
        "category": "A",
        "expect": "recurring",
        "concept": "backing a claim with a measurement",
        "why": ("All four sittings get a 'backing a claim with a measurement' "
                "question wrong, and three of them pick the same option - "
                "'offered a single impression where a tuning claim needs "
                "numbers'. That is one misconception recurring, not four "
                "unrelated slips."),
        "members": [
            "stu_f1228d0d00",  # 18/20 - 2 wrong, both this concept
            "stu_d5a01e41f9",  # 19/20 - 1 wrong, this concept
            "stu_93dfa11827",  # 17/20 - this concept + 2 others
            "stu_c70717f485",  # 17/20 - this concept + 2 others
        ],
    },
    {
        "id": "mem_cs_a",
        "display": "Arjun M.",
        "department": "computer_science",
        "category": "A",
        "expect": "recurring",
        "concept": "understanding what a variable holds",
        "why": ("Every sitting misses 'understanding what a variable holds', "
                "and three of the four pick the identical wrong option on "
                "cs_t4_q1 - treating `b = a` as making a copy. The strongest "
                "clean signal in the whole dataset."),
        "members": [
            "stu_2bf3073f73",  # 19/20 - 1 wrong, this concept, cs_t4_q1
            "stu_fb9298c06a",  # 19/20 - 1 wrong, this concept
            "stu_0cf341b68e",  # 17/20 - this concept incl. cs_t4_q1
            "stu_c744ac76e6",  # 15/20 - this concept x3
        ],
    },
    {
        "id": "mem_robotics_b",
        "display": "Karthik S.",
        "department": "robotics",
        "category": "B",
        "expect": "not_enough_evidence | similar | low confidence",
        "concept": None,
        "clean_control": True,
        "why": ("A true negative control: the three sittings share no wrong "
                "question AND no wrong concept, so there is provably nothing "
                "to find. Three sittings, not four - in 18 real robotics "
                "students no group of four with zero concept overlap exists, "
                "and padding it with a fourth would have smuggled a real "
                "pattern into the control."),
        "members": [
            "stu_010df982b7",  # method / movement order / robot position
            "stu_833fb269ea",  # weight and force / matching a fix
            "stu_f1228d0d00",  # measurement only
        ],
    },
    {
        "id": "mem_cs_b",
        "display": "Nithya V.",
        "department": "computer_science",
        "category": "B",
        "expect": "not_enough_evidence | similar | low confidence",
        "concept": None,
        "clean_control": False,
        "why": ("The weakest signal available in computer science, and NOT a "
                "clean control - we say so rather than pretend otherwise. No "
                "question is missed twice, but with only five CS concepts and "
                "13 students, no group of four exists with zero concept "
                "overlap: two sittings here both touch 'understanding what a "
                "variable holds' and two both touch 'backing up a claim with "
                "evidence'. If the system reports a recurrence it must cite "
                "one of those, and a professor can then judge whether two "
                "different questions on one concept is a pattern or a "
                "coincidence. That judgement is the professor's, which is the "
                "point."),
        "members": [
            "stu_2bf3073f73",  # variable holds, once
            "stu_b5cb2df8b5",  # data structure / evidence
            "stu_f834cd4135",  # code timing / evidence
            "stu_fb9298c06a",  # variable holds, once
        ],
    },
]


# ------------------------------------------------------------------ reading

def read_sitting(src: sqlite3.Connection, student_id: str) -> dict:
    """One real student's real answers, exactly as they gave them."""
    student = src.execute(
        "SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if student is None:
        raise SystemExit(f"no such student in {SOURCE_DB.name}: {student_id}")
    rows = [dict(r) for r in src.execute(
        "SELECT * FROM responses WHERE student_id=? ORDER BY question_id",
        (student_id,))]
    if len(rows) < 20:
        raise SystemExit(f"{student_id} has only {len(rows)} answers, not a "
                         "completed sitting")
    return {"student": dict(student), "responses": rows}


def evidence_for(responses: list[dict]) -> dict:
    """Turn twenty real answers into an EvidenceSet the flow accepts.

    Same shape app/quiz.py:attempt_from_answer builds, so nothing downstream
    can tell a replayed sitting from a live one. source_ref is
    "<question_id>#<chosen option>", which is what the citation check in
    handle_evidence_check matches findings against.
    """
    wrong = [r for r in responses if not r["correct"]]
    right = [r for r in responses if r["correct"]]

    items = [{
        "concept": r["concept"],
        "kind": "difficulty",
        "passage": f"chose option {r['chosen']} on {r['question_id']}"
                   + (f" - {r['misconception']}" if r["misconception"] else ""),
        "source_ref": f"{r['question_id']}#{r['chosen']}",
        "supported": True,
        "note": r["misconception"],
    } for r in wrong[:MAX_EVIDENCE]]

    for r in right[: MAX_EVIDENCE - len(items)]:
        items.append({
            "concept": r["concept"],
            "kind": "strength",
            "passage": f"chose option {r['chosen']} on {r['question_id']}",
            "source_ref": f"{r['question_id']}#{r['chosen']}",
            "supported": True,
            "note": None,
        })

    notes = []
    if len(wrong) > MAX_EVIDENCE:
        notes.append(f"{len(wrong) - MAX_EVIDENCE} further wrong answers in this "
                     "sitting are not cited here; the evidence set is capped at "
                     f"{MAX_EVIDENCE} items.")
    return {"items": items, "uncertainty_notes": notes, "unsupported_count": 0}


def attempt_for(group: dict, sitting_no: int, when: date, data: dict) -> dict:
    """The attempt record for one synthetic sitting."""
    responses = data["responses"]
    got = sum(r["correct"] for r in responses)
    wrong = [r for r in responses if not r["correct"]]
    concepts = sorted({r["concept"] for r in responses})

    summary = "; ".join(
        f"{r['question_id']}: chose {r['chosen']}"
        + (f" ({r['misconception']})" if r["misconception"] else "")
        for r in wrong) or "no incorrect answers"

    return {
        "student_id": group["id"],
        "assignment_id": f"diagnostic_sitting_{sitting_no}",
        "date": when.isoformat(),
        "course_context": (f"{group['department'].replace('_', ' ').title()} "
                           "diagnostic quiz, 20 questions"),
        "assignment_prompt": (
            f"Diagnostic quiz sitting {sitting_no} ({when.isoformat()}): "
            "20 multiple-choice questions across the department's core topics."),
        "learning_objectives": concepts,
        "submission": f"Scored {got}/20. Incorrect answers - {summary}",
        "precomputed_evidence": evidence_for(responses),
        "quiz_meta": {
            "score": got,
            "asked": len(responses),
            "sitting": sitting_no,
            # Provenance, carried in the record itself rather than in a doc
            # that can drift away from the data.
            "replayed_from_real_student": data["student"]["id"],
            "replayed_from_real_name": data["student"]["name"],
            "synthetic_timeline": True,
        },
    }


# --------------------------------------------------------------- validation

def validate(src: sqlite3.Connection, group: dict) -> list[str]:
    """Check a group really is the category it claims to be.

    This exists because the first version of these groups was wrong and the
    pipeline, not the author, is what caught it. A category B group that
    happens to contain a genuine repeated mistake is not a negative control -
    it is a positive case with the wrong label, and a demo built on it would be
    claiming the system failed when it had actually succeeded.

    Returns a list of complaints; empty means the group is what it says it is.
    """
    per_sitting = []
    for member in group["members"]:
        rows = src.execute(
            "SELECT question_id, chosen, concept FROM responses"
            " WHERE student_id=? AND correct=0", (member,)).fetchall()
        per_sitting.append({
            "member": member,
            "refs": {f"{r['question_id']}#{r['chosen']}" for r in rows},
            "questions": {r["question_id"] for r in rows},
            "concepts": {r["concept"] for r in rows},
        })

    problems = []
    if group["category"] == "A":
        concept = group["concept"]
        missing = [s["member"] for s in per_sitting if concept not in s["concepts"]]
        if missing:
            problems.append(
                f"category A claims every sitting misses {concept!r}, but "
                + ", ".join(missing) + " do(es) not")
    else:
        # No sitting may repeat another sitting's wrong question at all.
        seen_q: dict[str, str] = {}
        for s in per_sitting:
            for q in s["questions"]:
                if q in seen_q:
                    problems.append(
                        f"category B must have nothing to find, but {q} is "
                        f"answered wrongly by both {seen_q[q]} and {s['member']}")
                seen_q[q] = s["member"]
        if group.get("concept") is not None:
            problems.append("category B should not name a concept")

        # A group advertised as a CLEAN control must also share no concept.
        # Sharing a concept across two sittings is a legitimate thing for the
        # comparison step to call recurring, so a group that does share one is
        # a near-miss, not a control, and must not be labelled as one.
        if group.get("clean_control"):
            seen_c: dict[str, str] = {}
            for s_ in per_sitting:
                for c in s_["concepts"]:
                    if c in seen_c:
                        problems.append(
                            f"{group['id']} claims to be a clean control, but "
                            f"{c!r} is missed by both {seen_c[c]} and "
                            f"{s_['member']}")
                    seen_c[c] = s_["member"]
    return problems


# ------------------------------------------------------------------ writing

def build(src: sqlite3.Connection, store: Store, groups: list[dict]) -> list[dict]:
    complaints = [c for g in groups for c in validate(src, g)]
    if complaints:
        raise SystemExit("group selection is not what it claims:\n  - "
                         + "\n  - ".join(complaints))

    manifest = []
    for group in groups:
        sittings = []
        for i, member in enumerate(group["members"], start=1):
            data = read_sitting(src, member)
            if data["student"]["department"] != group["department"]:
                raise SystemExit(
                    f"{member} is {data['student']['department']}, but group "
                    f"{group['id']} is {group['department']}")
            when = FIRST_SITTING + timedelta(weeks=WEEKS_BETWEEN * (i - 1))
            attempt = attempt_for(group, i, when, data)

            run_id = store.create_run("recall", meta={
                "student_id": group["id"],
                "display_name": group["display"],
                "department": group["department"],
                "category": group["category"],
                "sitting": i,
                "synthetic_timeline": True,
                "replayed_from_real_student": member,
            })
            store.set_state(run_id, RunState.NEW_ATTEMPT)
            store.append(run_id, "attempt", attempt, produced_by="ingest:replay")

            # created_at is what history.py orders by, so it must reflect the
            # fabricated calendar, not the moment this script ran.
            store.db.execute(
                "UPDATE runs SET created_at=?, updated_at=? WHERE id=?",
                (time.mktime(when.timetuple()),) * 2 + (run_id,))

            sittings.append({
                "sitting": i, "run_id": run_id, "date": when.isoformat(),
                "assignment_id": attempt["assignment_id"],
                "real_student_id": member,
                "real_student_name": data["student"]["name"],
                "score": attempt["quiz_meta"]["score"],
                "wrong_concepts": dict(collections.Counter(
                    r["concept"] for r in data["responses"] if not r["correct"])),
            })

        manifest.append({**{k: v for k, v in group.items() if k != "members"},
                         "sittings": sittings})
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(SOURCE_DB))
    ap.add_argument("--target", default=str(TARGET_DB))
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing target database")
    args = ap.parse_args()

    source, target = Path(args.source), Path(args.target)
    if target.exists() and not args.force:
        raise SystemExit(f"{target} exists; pass --force to rebuild it")
    for suffix in ("", "-wal", "-shm"):
        p = target.with_name(target.name + suffix)
        if p.exists():
            p.unlink()

    # Copy rather than write into the live file: real students are still
    # submitting into webapp.db, and the fabricated timeline has no business
    # in the production record.
    src_ro = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    src_ro.row_factory = sqlite3.Row
    shutil.copy(source, target)
    print(f"copied {source.name} -> {target.name}")

    store = Store(target)
    manifest = build(src_ro, store, GROUPS)
    store.db.commit()

    out = ROOT / "docs" / "memory-demo-manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for g in manifest:
        print(f"\n[{g['category']}] {g['id']}  \"{g['display']}\"  "
              f"({g['department']}) - expect {g['expect']}")
        for s in g["sittings"]:
            print(f"   sitting {s['sitting']} {s['date']}  {s['score']}/20  "
                  f"{s['run_id']}  <- {s['real_student_name']}")
    print(f"\nmanifest -> {out.relative_to(ROOT)}")
    print(f"database -> {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
