"""Build a clean, two-tab Excel workbook documenting exactly who is in the
persistent-memory demo, which real student's real answers back each sitting,
and what week/date each sitting was backdated to.

Reads only docs/memory-demo-manifest.json and docs/memory-demo-results.json -
the same files the demo itself was built and verified from. Nothing here is
re-derived or guessed; every cell traces to one of those two files.

Run:
    .venv/bin/python tools/build_memory_demo_excel.py

Writes docs/memory-demo-roster.xlsx.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "memory-demo-manifest.json"
RESULTS = ROOT / "docs" / "memory-demo-results.json"
OUT = ROOT / "docs" / "memory-demo-roster.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F5F55")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=13)
NOTE_FONT = Font(italic=True, size=9, color="6E6A61")


def _week_label(first_date: date, this_date: date) -> str:
    delta_days = (this_date - first_date).days
    week_no = delta_days // 7 + 1
    return f"Week {week_no}"


def _style_header(ws, row: int, n_cols: int) -> None:
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def _autosize(ws, widths: dict[int, int]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def build() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results_by_id = {
        g["id"]: g for g in json.loads(RESULTS.read_text(encoding="utf-8"))
    }

    wb = Workbook()

    # --------------------------------------------------------- sheet 1: detail
    ws = wb.active
    ws.title = "Sittings (detail)"

    ws["A1"] = "Recall — Persistent-memory demo: who is in it, sitting by sitting"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:L1")
    ws["A2"] = (
        "Every row is one real student's real 20-question answers, replayed as "
        "one sitting of a fabricated identity. Only the calendar date is "
        "invented — the answers, the student, and the score are real."
    )
    ws["A2"].font = NOTE_FONT
    ws.merge_cells("A2:L2")

    headers = [
        "Identity (shown in demo)", "Department", "Category", "Sitting #",
        "Week (relative)", "Sitting date", "Real student name",
        "Real student id", "Score /20", "Agent label", "Cited earlier evidence?",
        "Paused for human review?",
    ]
    header_row = 4
    for i, h in enumerate(headers, start=1):
        ws.cell(row=header_row, column=i, value=h)
    _style_header(ws, header_row, len(headers))
    ws.freeze_panes = f"A{header_row + 1}"

    r = header_row + 1
    for g in manifest:
        gid = g["id"]
        res = results_by_id.get(gid, {})
        res_sittings = {s["sitting"]: s for s in res.get("sittings", [])}
        sittings = sorted(g["sittings"], key=lambda s: s["sitting"])
        if not sittings:
            continue
        first_date = datetime.strptime(sittings[0]["date"], "%Y-%m-%d").date()

        for s in sittings:
            this_date = datetime.strptime(s["date"], "%Y-%m-%d").date()
            rs = res_sittings.get(s["sitting"], {})
            label = rs.get("label", "")
            cited = bool(rs.get("related_refs"))
            paused = bool(rs.get("paused_for_human"))

            ws.cell(row=r, column=1, value=g["display"])
            ws.cell(row=r, column=2,
                     value=g["department"].replace("_", " ").title())
            ws.cell(row=r, column=3,
                     value=f'{g["category"]} — '
                           f'{"clean pattern" if g["category"] == "A" else "erratic / near-miss"}')
            ws.cell(row=r, column=4, value=s["sitting"])
            ws.cell(row=r, column=5, value=_week_label(first_date, this_date))
            ws.cell(row=r, column=6, value=s["date"])
            ws.cell(row=r, column=7, value=s["real_student_name"])
            ws.cell(row=r, column=8, value=s["real_student_id"])
            ws.cell(row=r, column=9, value=s["score"])
            ws.cell(row=r, column=10, value=label)
            ws.cell(row=r, column=11, value="Yes" if cited else "No")
            ws.cell(row=r, column=12, value="Yes" if paused else "No")
            r += 1

    _autosize(ws, {
        1: 20, 2: 18, 3: 26, 4: 9, 5: 14, 6: 13,
        7: 26, 8: 16, 9: 9, 10: 20, 11: 20, 12: 20,
    })

    # -------------------------------------------------------- sheet 2: summary
    ws2 = wb.create_sheet("Identities (summary)")
    ws2["A1"] = "One row per synthetic identity"
    ws2["A1"].font = TITLE_FONT
    ws2.merge_cells("A1:H1")

    headers2 = [
        "Identity", "Department", "Category", "Sittings", "Real students behind it",
        "Why this department/category", "Final label", "Met expectation?",
    ]
    for i, h in enumerate(headers2, start=1):
        ws2.cell(row=3, column=i, value=h)
    _style_header(ws2, 3, len(headers2))
    ws2.freeze_panes = "A4"

    r = 4
    for g in manifest:
        gid = g["id"]
        res = results_by_id.get(gid, {})
        names = ", ".join(
            sorted({s["real_student_name"] for s in g["sittings"]})
        )
        ws2.cell(row=r, column=1, value=g["display"])
        ws2.cell(row=r, column=2, value=g["department"].replace("_", " ").title())
        ws2.cell(row=r, column=3,
                 value=f'{g["category"]} — '
                       f'{"clean pattern" if g["category"] == "A" else "erratic / near-miss"}')
        ws2.cell(row=r, column=4, value=len(g["sittings"]))
        ws2.cell(row=r, column=5, value=names)
        ws2.cell(row=r, column=6, value=g.get("why", ""))
        ws2.cell(row=r, column=7, value=res.get("final_label", ""))
        ws2.cell(row=r, column=8,
                 value="Yes" if res.get("meets_expectation") else "No")
        ws2.cell(row=r, column=6).alignment = Alignment(wrap_text=True, vertical="top")
        r += 1

    _autosize(ws2, {1: 18, 2: 18, 3: 26, 4: 10, 5: 34, 6: 80, 7: 20, 8: 16})
    for row in ws2.iter_rows(min_row=4, max_row=r - 1):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
