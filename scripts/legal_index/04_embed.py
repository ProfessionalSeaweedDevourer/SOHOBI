#!/usr/bin/env python3
"""
Legal index pipeline — 4단계: Azure OpenAI 임베딩.

text-embedding-3-small (1536d) 기준. batch_size 16, exponential backoff.
입력의 embeddingText 필드를 임베딩하여 contentVector 필드 추가.

환경변수: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
         AZURE_EMBEDDING_DEPLOYMENT (기본 'text-embedding-3-small')
         AZURE_OPENAI_API_VERSION (기본 '2024-08-01-preview')
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from openai import AzureOpenAI
except ImportError:
    print(
        "ERROR: openai package not installed. Run: pip install openai", file=sys.stderr
    )
    sys.exit(1)


def make_client() -> AzureOpenAI:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    return AzureOpenAI(
        api_key=api_key, api_version=api_version, azure_endpoint=endpoint
    )


def embed_batch(
    client: AzureOpenAI, deployment: str, texts: list[str], max_retries: int = 5
) -> list[list[float]]:
    delay = 1.0
    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(model=deployment, input=texts)
            return [d.embedding for d in resp.data]
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(
                f"WARN attempt {attempt + 1}: {e} — retry in {delay:.1f}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument(
        "--limit", type=int, default=None, help="앞에서 N개만 처리(테스트용)"
    )
    args = p.parse_args()

    deployment = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    client = make_client()
    in_path = Path(args.input)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    with in_path.open(encoding="utf-8") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if args.limit and len(records) >= args.limit:
                break

    print(
        f"embedding {len(records)} records (deployment={deployment}, batch={args.batch_size})"
    )

    written = 0
    with out_path.open("w", encoding="utf-8") as fout:
        for i in range(0, len(records), args.batch_size):
            batch = records[i : i + args.batch_size]
            texts = [r["embeddingText"] for r in batch]
            vectors = embed_batch(client, deployment, texts)
            for r, vec in zip(batch, vectors):
                r["contentVector"] = vec
                fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                written += 1
            if (i // args.batch_size) % 10 == 0:
                print(f"  {written}/{len(records)}")

    print(f"embedded {written} records -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
