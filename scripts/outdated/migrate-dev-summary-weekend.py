#!/usr/bin/env python3
"""주말(토·일) dev-summary 파일의 모든 커밋을 '근무 외'로 재분류하는 일회성 스크립트."""

import re
from datetime import date
from pathlib import Path

SUMMARY_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "dev-summary"
FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")
TABLE_HEADER = "| 시각 (KST) | PR | 제목 | 내용 |\n|-----------|-----|------|------|"
TIME_RE = re.compile(r"^\|\s*(\d{1,2}):(\d{2})\b")


def time_key(row: str) -> int:
    m = TIME_RE.match(row)
    if not m:
        return 10**9
    return int(m.group(1)) * 60 + int(m.group(2))


def extract_rows(lines: list[str], header_idx: int) -> tuple[int, int, list[str]]:
    """header_idx = '| 시각 (KST)'의 위치. (end_idx_exclusive, separator_idx, rows)를 반환."""
    rows: list[str] = []
    i = header_idx + 1
    if i < len(lines) and re.match(r"^\|[-| ]+\|$", lines[i].strip()):
        i += 1
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(lines[i])
        i += 1
    return i, header_idx + 1, rows


def migrate(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 1) 섹션별 헤더 인덱스
    work_header_line = None
    off_header_line = None
    for i, line in enumerate(lines):
        if line.startswith("## 작업 내역"):
            work_header_line = i
        elif line.startswith("## 근무 외 작업"):
            off_header_line = i

    if work_header_line is None:
        return False

    # 2) 작업 내역 테이블/본문 파싱
    work_rows: list[str] = []
    work_block_end = None
    work_table_start = None
    for j in range(work_header_line + 1, len(lines)):
        if lines[j].startswith("| 시각"):
            work_table_start = j
            work_block_end, _, work_rows = extract_rows(lines, j)
            break
        if lines[j].startswith("## "):
            work_block_end = j
            break
    if work_block_end is None:
        work_block_end = len(lines)

    # 3) 근무 외 테이블 파싱
    off_rows: list[str] = []
    off_block_end = None
    off_table_start = None
    if off_header_line is not None:
        for j in range(off_header_line + 1, len(lines)):
            if lines[j].startswith("| 시각"):
                off_table_start = j
                off_block_end, _, off_rows = extract_rows(lines, j)
                break
            if lines[j].startswith("## "):
                off_block_end = j
                break
        if off_block_end is None:
            off_block_end = len(lines)

    # 4) 병합 + 시각 순 정렬 (안정 정렬)
    merged = sorted(work_rows + off_rows, key=time_key)
    total = len(merged)

    # 5) 새 섹션 블록 빌드
    new_work_block = [
        lines[work_header_line],
        "",
        "(정상 근무 시간 내 작업 없음)",
        "",
    ]
    new_off_block = [
        "## 근무 외 작업",
        "",
        TABLE_HEADER,
        *merged,
        "",
    ]

    # 6) 기존 작업 내역~근무 외 작업 구간을 통째로 교체
    replace_start = work_header_line
    if off_header_line is not None:
        replace_end = off_block_end
    else:
        replace_end = work_block_end

    new_lines = lines[:replace_start] + new_work_block + new_off_block + lines[replace_end:]

    # 7) 개요 표 '정상 근무' / '근무 외' 행 갱신
    for k, line in enumerate(new_lines):
        if line.startswith("| 정상 근무"):
            new_lines[k] = "| 정상 근무 | 0건 (09:30~18:20, 주말) |"
        elif line.startswith("| 근무 외"):
            new_lines[k] = f"| 근무 외 | {total}건 |"

    out = "\n".join(new_lines)
    if not out.endswith("\n"):
        out += "\n"
    if out == text:
        return False
    path.write_text(out, encoding="utf-8")
    return True


def main() -> None:
    touched = 0
    scanned = 0
    for md in sorted(SUMMARY_DIR.glob("*/*.md")):
        m = FILENAME_RE.match(md.name)
        if not m:
            continue
        y, mo, d = (int(x) for x in m.groups())
        if date(y, mo, d).weekday() < 5:
            continue
        scanned += 1
        if migrate(md):
            print(f"  ✅ {md.relative_to(SUMMARY_DIR)}")
            touched += 1
        else:
            print(f"  ⏭️  {md.relative_to(SUMMARY_DIR)}")

    print(f"\n주말 파일 {scanned}개 중 {touched}개 갱신")


if __name__ == "__main__":
    main()
