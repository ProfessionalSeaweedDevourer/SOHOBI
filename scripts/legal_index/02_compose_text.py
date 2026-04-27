#!/usr/bin/env python3
"""
Legal index pipeline — 2단계: 임베딩 입력 텍스트 구성.

각 record에 embeddingText 필드 추가:
  [{lawName} > {chapterTitle} > {sectionTitle}] {articleTitle} (n/m) {content}

- chapterTitle/sectionTitle 누락 시 생략
- totalChunks==1 일 때 (n/m) 마커 생략
- 표 포함 청크는 끝에 (표 포함 — 원문 참조 권장) 안내 부착
"""

import argparse
import json
import sys
from pathlib import Path


def compose_embedding_text(r: dict) -> str:
    parts = [r["lawName"]]
    if r.get("chapterTitle"):
        parts.append(r["chapterTitle"])
    if r.get("sectionTitle"):
        parts.append(r["sectionTitle"])
    breadcrumb = "[" + " > ".join(parts) + "]"

    article_title = r.get("articleTitle", "").strip()

    chunk_marker = ""
    total = r.get("totalChunks", 1)
    if total > 1:
        chunk_marker = f" ({r['chunkIndex'] + 1}/{total})"

    body = r.get("content", "").strip()
    # content가 articleTitle로 시작하면 중복 제거 (embeddingText 토큰 절약)
    if article_title and body.startswith(article_title):
        body = body[len(article_title) :].lstrip()

    text = f"{breadcrumb} {article_title}{chunk_marker} {body}".strip()

    if r.get("hasTable"):
        text += "\n\n(본 조항은 표/서식을 포함합니다 — 원문 참조 권장)"

    return text


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_in, n_out, total_chars = 0, 0, 0
    with (
        in_path.open(encoding="utf-8") as fin,
        out_path.open("w", encoding="utf-8") as fout,
    ):
        for line in fin:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            r = json.loads(line)
            r["embeddingText"] = compose_embedding_text(r)
            total_chars += len(r["embeddingText"])
            fout.write(json.dumps(r, ensure_ascii=False) + "\n")
            n_out += 1

    print(f"composed {n_out}/{n_in} records")
    print(f"avg embeddingText length: {total_chars // max(n_out, 1)} chars")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
