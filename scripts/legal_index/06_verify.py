#!/usr/bin/env python3
"""
Legal index pipeline — 6단계: 검증.

- 인덱스 row count
- lawName facet 분포
- 표본 query 5개 → score 분포 + top1 결과 출력

환경변수: AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY
"""

import argparse
import os
import sys

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
except ImportError:
    print("ERROR: azure-search-documents not installed.", file=sys.stderr)
    sys.exit(1)

SAMPLE_QUERIES = [
    "음식점 영업허가 절차",
    "최저임금 위반 시 처벌",
    "개인정보 동의 받지 않고 수집",
    "소상공인 정책자금 지원 대상",
    "일반음식점 면적 기준",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--sample", type=int, default=5)
    args = p.parse_args()

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    client = SearchClient(endpoint, args.index, AzureKeyCredential(key))

    count = client.get_document_count()
    print(f"index '{args.index}' document count: {count}")

    print("\n=== lawName facet ===")
    results = client.search("*", facets=["lawName,count:50"], top=0)
    facets = results.get_facets()
    for f in facets.get("lawName", [])[:30]:
        print(f"  {f['value']}: {f['count']}")

    print(f"\n=== sample queries (top {args.sample}) ===")
    for q in SAMPLE_QUERIES:
        print(f"\nQ: {q}")
        results = list(client.search(search_text=q, top=args.sample))
        for r in results:
            score = r.get("@search.score", 0)
            print(
                f"  [{score:.3f}] {r.get('lawName')} {r.get('articleTitle')} (chunk {r.get('chunkIndex')})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
