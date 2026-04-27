#!/usr/bin/env python3
"""
Legal index pipeline — 1단계: 청크 정리.

- title-only chunkIndex=0 (e.g., '제37조(영업허가 등)' 12자 단독) 제거
- [표/서식 이미지] 토큰 다회 등장 → 1회로 정규화
- ASCII 박스 라인 (┌─│└┴┬┤├═║) 제거
- hasTable, lawCategory, articleId, totalChunks 메타 부여

입력: refined_law_data*.json (list of records)
출력: cleaned.jsonl (1 record/line)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ASCII_BOX_RE = re.compile(r"^[\s┌─│└┴┬┤├═║┐┘┼━┃╋]+$")
TABLE_TOKEN_RE = re.compile(r"\[표/서식 이미지\]")
MULTI_TABLE_TOKEN_RE = re.compile(r"(\[표/서식 이미지\]\s*){2,}")
WHITESPACE_RE = re.compile(r"\n{3,}")


def classify_law_category(law_name: str) -> str:
    if law_name.endswith("시행규칙"):
        return "시행규칙"
    if law_name.endswith("시행령"):
        return "시행령"
    return "본법"


def clean_content(content: str) -> tuple[str, bool]:
    """ASCII 표·표 토큰 정리. (cleaned, had_table) 반환."""
    had_table = bool(TABLE_TOKEN_RE.search(content) or "┌" in content or "│" in content)

    content = MULTI_TABLE_TOKEN_RE.sub("[표 생략]", content)
    content = TABLE_TOKEN_RE.sub("[표 생략]", content)

    lines = []
    for line in content.split("\n"):
        if ASCII_BOX_RE.match(line):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = WHITESPACE_RE.sub("\n\n", cleaned).strip()
    return cleaned, had_table


def is_title_only(record: dict) -> bool:
    """chunkIndex=0이 articleTitle만 담은 경우(노이즈)."""
    if not record.get("isChunked"):
        return False
    if record.get("chunkIndex") != 0:
        return False
    content = record.get("content", "").strip()
    article_title = record.get("articleTitle", "").strip()
    if not article_title:
        return False
    return content == article_title or (
        content.startswith(article_title) and len(content) <= len(article_title) + 5
    )


def process_records(records: list[dict]) -> tuple[list[dict], dict]:
    stats = {
        "in": len(records),
        "removed_title_only": 0,
        "had_table": 0,
        "out": 0,
    }

    by_article: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        by_article[(r["mst"], r["articleNo"])].append(r)

    out: list[dict] = []
    for (mst, art_no), group in by_article.items():
        group_sorted = sorted(group, key=lambda x: x.get("chunkIndex", 0))
        kept = [r for r in group_sorted if not is_title_only(r)]
        stats["removed_title_only"] += len(group_sorted) - len(kept)

        total_chunks = len(kept)
        for new_idx, r in enumerate(kept):
            cleaned, had_table = clean_content(r["content"])
            if had_table:
                stats["had_table"] += 1
            out.append(
                {
                    **r,
                    "content": cleaned,
                    "chunkIndex": new_idx,
                    "totalChunks": total_chunks,
                    "hasTable": had_table,
                    "lawCategory": classify_law_category(r["lawName"]),
                    "articleId": f"law_{mst}_{art_no}",
                }
            )

    stats["out"] = len(out)
    return out, stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--in", dest="inputs", nargs="+", required=True, help="입력 JSON 파일들"
    )
    p.add_argument("--out", required=True, help="출력 JSONL 경로")
    args = p.parse_args()

    all_records: list[dict] = []
    for path in args.inputs:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
            if not isinstance(data, list):
                print(f"FATAL: {path} is not a JSON list", file=sys.stderr)
                return 1
            all_records.extend(data)

    cleaned, stats = process_records(all_records)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        for r in cleaned:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"input records:           {stats['in']}")
    print(f"removed (title-only):    {stats['removed_title_only']}")
    print(f"records w/ tables:       {stats['had_table']}")
    print(f"output records:          {stats['out']}")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
