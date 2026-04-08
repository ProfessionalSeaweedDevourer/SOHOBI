#!/usr/bin/env python3
"""기존 dev-summary 파일에 근무 시간 분류를 적용하는 일회성 마이그레이션 스크립트."""

import re
from pathlib import Path

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "docs" / "dev-summary"
WORK_START = (9, 30)
WORK_END = (18, 20)

TABLE_HEADER = "| 시각 (KST) | PR | 내용 |\n|-----------|-----|------|"


def parse_time(time_str: str) -> tuple[int, int] | None:
    m = re.match(r"(\d{1,2}):(\d{2})", time_str.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def is_work_hours(h: int, m: int) -> bool:
    t = h * 60 + m
    return WORK_START[0] * 60 + WORK_START[1] <= t <= WORK_END[0] * 60 + WORK_END[1]


def migrate_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")

    # Skip already migrated files
    if "## 근무 외 작업" in text:
        return False

    lines = text.split("\n")

    # Find the 작업 내역 table rows
    table_start = None
    table_rows = []
    for i, line in enumerate(lines):
        if line.startswith("| 시각 (KST)"):
            table_start = i
            continue
        if table_start is not None and i == table_start + 1:
            # separator line
            continue
        if table_start is not None and line.startswith("|"):
            table_rows.append((i, line))
        elif table_start is not None and not line.startswith("|"):
            break

    if not table_rows:
        return False

    # Classify rows
    work_rows = []
    off_rows = []
    for _, row in table_rows:
        cols = [c.strip() for c in row.split("|")]
        # cols: ['', '시각', 'PR', '내용', '']
        time_str = cols[1] if len(cols) > 1 else ""
        t = parse_time(time_str)
        if t and is_work_hours(*t):
            work_rows.append(row)
        else:
            off_rows.append(row)

    work_count = len(work_rows)
    off_count = len(off_rows)

    # Rebuild the overview table — add 정상 근무 / 근무 외 rows
    new_lines = []
    pr_row_passed = False
    for line in lines:
        # Insert after PR 수 row
        if line.startswith("| PR 수"):
            new_lines.append(line)
            new_lines.append(f"| 정상 근무 | {work_count}건 (09:30~18:20) |")
            new_lines.append(f"| 근무 외 | {off_count}건 |")
            pr_row_passed = True
            continue
        # Skip old 작업 내역 section — we'll rebuild it
        new_lines.append(line)

    text = "\n".join(new_lines)

    # Rebuild 작업 내역 section
    if work_rows:
        work_table = TABLE_HEADER + "\n" + "\n".join(work_rows)
    else:
        work_table = "(정상 근무 시간 내 작업 없음)"

    # Replace old table with classified version
    # Find and replace the 작업 내역 section
    pattern = r"(## 작업 내역\n\n)(\| 시각.*?\n\|[-| ]+\n(?:\|.*\n?)*)"
    if off_rows:
        off_table = f"\n\n## 근무 외 작업\n\n{TABLE_HEADER}\n" + "\n".join(off_rows)
        replacement = r"\g<1>" + work_table + off_table
    else:
        replacement = r"\g<1>" + work_table

    text = re.sub(pattern, replacement, text)

    # Ensure file ends with newline
    if not text.endswith("\n"):
        text += "\n"

    path.write_text(text, encoding="utf-8")
    return True


def main():
    migrated = 0
    skipped = 0
    for md_file in sorted(SUMMARY_DIR.glob("*/*.md")):
        if md_file.name == ".gitkeep":
            continue
        if migrate_file(md_file):
            off_tag = ""
            text = md_file.read_text()
            if "## 근무 외 작업" in text:
                off_tag = " (근무 외 있음)"
            print(f"  ✅ {md_file.relative_to(SUMMARY_DIR)}{off_tag}")
            migrated += 1
        else:
            print(f"  ⏭️  {md_file.relative_to(SUMMARY_DIR)} (skip)")
            skipped += 1

    print(f"\n완료: {migrated}개 변환, {skipped}개 스킵")


if __name__ == "__main__":
    main()
