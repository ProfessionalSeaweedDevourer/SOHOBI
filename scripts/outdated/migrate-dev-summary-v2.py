#!/usr/bin/env python3
"""기존 dev-summary 파일을 4컬럼(시각/PR/제목/내용) 포맷으로 변환.

git log에서 커밋 본문을 역추적하고, 본문의 핵심 변경사항을 요약하여
'내용' 컬럼에 삽입한다.
"""

import re
import subprocess
from pathlib import Path

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "docs" / "dev-summary"

# ──────────────────────────────────────────────
# 1. git log → commit lookup 구축
# ──────────────────────────────────────────────


def build_commit_lookup() -> dict:
    """hash(7) → body, PR# → body 매핑 구축."""
    raw = subprocess.check_output(
        ["git", "log", "origin/main", "--format=@@@%H|%s\n%b"],
        text=True,
    )
    lookup_hash = {}  # hash7 → (subject, body)
    lookup_pr = {}  # PR# → (subject, body)

    for record in raw.split("@@@"):
        record = record.strip()
        if not record:
            continue
        lines = record.split("\n", 1)
        header = lines[0]
        body = lines[1].strip() if len(lines) > 1 else ""

        pipe_idx = header.find("|")
        if pipe_idx < 0:
            continue
        full_hash = header[:pipe_idx]
        subject = header[pipe_idx + 1 :]
        hash7 = full_hash[:7]

        lookup_hash[hash7] = (subject, body)

        # PR# 추출
        m = re.search(r"\(#(\d+)\)", subject) or re.search(r"#(\d+)", subject)
        if m:
            lookup_pr[m.group(1)] = (subject, body)

    return lookup_hash, lookup_pr


def summarize_body(body: str) -> str:
    """커밋 본문에서 핵심 변경사항을 1-3줄로 요약."""
    if not body:
        return "-"

    # squash merge 본문에서 주요 변경 항목 추출
    # 패턴: "- 내용" 또는 "* 제목" 줄
    bullet_lines = []
    sub_commit_titles = []

    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("* "):
            # sub-commit 제목 (squash merge)
            # "* feat: ..." → "feat: ..." 에서 prefix 제거
            title = line[2:].strip()
            title = re.sub(
                r"^(feat|fix|refactor|chore|docs|style|perf|ci|test|revert):\s*",
                "",
                title,
            )
            if title:
                sub_commit_titles.append(title)
        elif line.startswith("- "):
            detail = line[2:].strip()
            # 너무 긴 항목은 잘라냄
            if len(detail) > 80:
                detail = detail[:77] + "..."
            bullet_lines.append(detail)

    # 전략: sub-commit 제목이 있으면 그걸 기반으로, 없으면 bullet 항목 사용
    if sub_commit_titles:
        # sub-commit 제목들을 합치되 3줄 이내
        result_lines = []
        for t in sub_commit_titles[:4]:  # max 4개
            result_lines.append(t)
        result = "<br>".join(result_lines[:3])
        if len(sub_commit_titles) > 3:
            result += f" 외 {len(sub_commit_titles) - 3}건"
        return result

    if bullet_lines:
        # bullet 항목 중 중요한 것만 선별 (최대 5개 → 3줄로 합침)
        selected = bullet_lines[:5]
        # 짧은 항목들은 합쳐서 한 줄로
        merged = []
        current = ""
        for item in selected:
            candidate = f"{current}, {item}" if current else item
            if len(candidate) > 80:
                if current:
                    merged.append(current)
                current = item
            else:
                current = candidate
        if current:
            merged.append(current)
        return "<br>".join(merged[:3])

    # 구조화된 항목이 없으면 본문 첫 줄
    first_line = body.split("\n")[0].strip()
    if first_line:
        return first_line[:80]
    return "-"


# ──────────────────────────────────────────────
# 2. 파일 파싱 및 변환
# ──────────────────────────────────────────────

TABLE_HEADER_3COL = "| 시각 (KST) | PR | 내용 |"
TABLE_SEP_3COL = "|-----------|-----|------|"
TABLE_HEADER_4COL = "| 시각 (KST) | PR | 제목 | 내용 |"
TABLE_SEP_4COL = "|-----------|-----|------|------|"


def extract_pr_number(pr_cell: str) -> str | None:
    """PR 셀에서 번호 추출: '[#123](url)' → '123', '`abcdef1`' → None."""
    m = re.search(r"#(\d+)", pr_cell)
    return m.group(1) if m else None


def extract_hash(pr_cell: str) -> str | None:
    """`abcdef1` 형태에서 hash7 추출."""
    m = re.search(r"`([0-9a-f]{7})`", pr_cell)
    return m.group(1) if m else None


def migrate_file(path: Path, lookup_hash: dict, lookup_pr: dict) -> bool:
    text = path.read_text(encoding="utf-8")

    # 이미 4컬럼이면 스킵
    if "| 제목 |" in text or TABLE_HEADER_4COL in text:
        return False

    lines = text.split("\n")
    new_lines = []
    in_table = False
    skip_sep = False

    for i, line in enumerate(lines):
        # 3컬럼 헤더 → 4컬럼으로 교체
        if line.strip() == TABLE_HEADER_3COL:
            new_lines.append(TABLE_HEADER_4COL)
            in_table = True
            skip_sep = True
            continue

        if skip_sep and line.strip() == TABLE_SEP_3COL:
            new_lines.append(TABLE_SEP_4COL)
            skip_sep = False
            continue

        skip_sep = False

        # 테이블 행 변환
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")]
            # cols: ['', 시각, PR, 내용, '']
            if len(cols) >= 5:
                time_col = cols[1]
                pr_col = cols[2]
                old_content = cols[3]

                # 커밋 본문 조회
                body_summary = "-"
                pr_num = extract_pr_number(pr_col)
                hash7 = extract_hash(pr_col)

                if pr_num and pr_num in lookup_pr:
                    _, body = lookup_pr[pr_num]
                    body_summary = summarize_body(body)
                elif hash7 and hash7 in lookup_hash:
                    _, body = lookup_hash[hash7]
                    body_summary = summarize_body(body)

                # 제목: 기존 '내용'에서 PR번호 suffix 제거
                title = re.sub(r"\s*\(#\d+\)\s*$", "", old_content).strip()

                new_lines.append(
                    f"| {time_col} | {pr_col} | {title} | {body_summary} |"
                )
                continue
            else:
                in_table = False
        elif in_table and not line.startswith("|"):
            in_table = False

        new_lines.append(line)

    result = "\n".join(new_lines)
    if not result.endswith("\n"):
        result += "\n"

    path.write_text(result, encoding="utf-8")
    return True


def main():
    print("git log에서 커밋 본문 로드 중...")
    lookup_hash, lookup_pr = build_commit_lookup()
    print(f"  hash: {len(lookup_hash)}개, PR: {len(lookup_pr)}개 매핑 완료\n")

    migrated = 0
    skipped = 0
    for md_file in sorted(SUMMARY_DIR.glob("*/*.md")):
        if md_file.name == ".gitkeep":
            continue
        if migrate_file(md_file, lookup_hash, lookup_pr):
            print(f"  ✅ {md_file.relative_to(SUMMARY_DIR)}")
            migrated += 1
        else:
            print(f"  ⏭️  {md_file.relative_to(SUMMARY_DIR)} (이미 4컬럼)")
            skipped += 1

    print(f"\n완료: {migrated}개 변환, {skipped}개 스킵")


if __name__ == "__main__":
    main()
