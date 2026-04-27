#!/usr/bin/env python3
"""
Legal index 평가 — Recall@5, MRR, nDCG@10.

평가셋 형식 (JSONL, 1줄/문항):
  {"id": "Q001", "question": "음식점 영업허가 절차", "gold_article_ids": ["law_277149_37"]}

gold_article_ids 는 articleId 기준 (mst_articleNo). 한 문항에 여러 정답 article 허용 (OR).

검색 후처리: chunk → articleId로 group, group의 best score를 article score로 사용.

환경변수: AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
except ImportError:
    print("ERROR: azure-search-documents not installed.", file=sys.stderr)
    sys.exit(1)


def search_articles(
    client: SearchClient, query: str, k: int = 30
) -> list[tuple[str, float]]:
    """검색 후 articleId로 group, (articleId, best_score) list 반환."""
    raw = list(client.search(search_text=query, top=k))
    by_article: dict[str, float] = {}
    for r in raw:
        aid = r.get("articleId") or f"law_{r.get('mst', '?')}_{r.get('articleNo', '?')}"
        score = r.get("@search.score", 0.0)
        if aid not in by_article or score > by_article[aid]:
            by_article[aid] = score
    return sorted(by_article.items(), key=lambda x: -x[1])


def recall_at_k(ranked_aids: list[str], gold_aids: set[str], k: int) -> float:
    return 1.0 if gold_aids.intersection(ranked_aids[:k]) else 0.0


def mrr(ranked_aids: list[str], gold_aids: set[str]) -> float:
    for i, aid in enumerate(ranked_aids, start=1):
        if aid in gold_aids:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_aids: list[str], gold_aids: set[str], k: int) -> float:
    dcg = 0.0
    for i, aid in enumerate(ranked_aids[:k], start=1):
        if aid in gold_aids:
            dcg += 1.0 / math.log2(i + 1)
    ideal_hits = min(len(gold_aids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--eval-set", required=True)
    p.add_argument("--k", type=int, default=30, help="검색 over-fetch")
    args = p.parse_args()

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    client = SearchClient(endpoint, args.index, AzureKeyCredential(key))

    eval_path = Path(args.eval_set)
    cases = []
    with eval_path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))

    if not cases:
        print(f"FATAL: no eval cases in {eval_path}", file=sys.stderr)
        return 1

    print(f"evaluating {len(cases)} cases on index '{args.index}'\n")

    sums = {"recall@5": 0.0, "recall@10": 0.0, "mrr": 0.0, "ndcg@10": 0.0}
    misses: list[dict] = []

    for c in cases:
        gold = set(c["gold_article_ids"])
        ranked = search_articles(client, c["question"], k=args.k)
        ranked_aids = [aid for aid, _ in ranked]

        r5 = recall_at_k(ranked_aids, gold, 5)
        r10 = recall_at_k(ranked_aids, gold, 10)
        m = mrr(ranked_aids, gold)
        n = ndcg_at_k(ranked_aids, gold, 10)

        sums["recall@5"] += r5
        sums["recall@10"] += r10
        sums["mrr"] += m
        sums["ndcg@10"] += n

        if r10 == 0:
            misses.append(
                {
                    "id": c["id"],
                    "question": c["question"],
                    "gold": list(gold),
                    "top5_ranked": ranked_aids[:5],
                }
            )

    n_total = len(cases)
    print("=== Aggregate metrics ===")
    print(f"Recall@5  : {sums['recall@5'] / n_total:.4f}")
    print(f"Recall@10 : {sums['recall@10'] / n_total:.4f}")
    print(f"MRR       : {sums['mrr'] / n_total:.4f}")
    print(f"nDCG@10   : {sums['ndcg@10'] / n_total:.4f}")

    if misses:
        print(f"\n=== Misses ({len(misses)}/{n_total}) ===")
        for m in misses[:10]:
            print(f"  {m['id']}: {m['question']}")
            print(f"    gold: {m['gold']}")
            print(f"    top5: {m['top5_ranked']}")
        if len(misses) > 10:
            print(f"  ... ({len(misses) - 10} more)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
