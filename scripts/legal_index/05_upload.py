#!/usr/bin/env python3
"""
Legal index pipeline — 5단계: Azure AI Search 업로드.

--create-if-missing 시 legal-index-v2 스키마(기획안 §3-1)로 인덱스 생성.
업로드는 1000 docs/batch, mergeOrUpload (재실행 멱등).

환경변수: AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        HnswParameters,
        LexicalAnalyzerName,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        VectorSearch,
        VectorSearchProfile,
    )
except ImportError:
    print("ERROR: azure-search-documents not installed.", file=sys.stderr)
    print("  Run: pip install azure-search-documents>=11.4.0", file=sys.stderr)
    sys.exit(1)


def build_index(name: str, dims: int = 1536) -> SearchIndex:
    ko = LexicalAnalyzerName.KO_LUCENE
    fields = [
        SearchField(
            name="id", type=SearchFieldDataType.String, key=True, filterable=True
        ),
        SearchField(
            name="lawName",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
            analyzer_name=ko,
        ),
        SearchField(
            name="lawCategory",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchField(name="mst", type=SearchFieldDataType.String, filterable=True),
        SearchField(name="articleNo", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="articleId",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="articleTitle",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=ko,
        ),
        SearchField(
            name="chapterTitle",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=ko,
        ),
        SearchField(
            name="sectionTitle",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=ko,
        ),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=ko,
        ),
        SearchField(name="fullText", type=SearchFieldDataType.String, searchable=False),
        SearchField(
            name="embeddingText", type=SearchFieldDataType.String, searchable=False
        ),
        SearchField(
            name="chunkIndex",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="totalChunks", type=SearchFieldDataType.Int32, filterable=True
        ),
        SearchField(
            name="isChunked", type=SearchFieldDataType.Boolean, filterable=True
        ),
        SearchField(name="hasTable", type=SearchFieldDataType.Boolean, filterable=True),
        SearchField(
            name="docType",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="enforceDate",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="promulgationNo", type=SearchFieldDataType.String, filterable=True
        ),
        SearchField(
            name="revisionType", type=SearchFieldDataType.String, filterable=True
        ),
        SearchField(name="source", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=dims,
            vector_search_profile_name="default",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-default",
                parameters=HnswParameters(m=4, ef_construction=400, metric="cosine"),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default", algorithm_configuration_name="hnsw-default"
            )
        ],
    )

    semantic = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="legal-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="articleTitle"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="lawName"),
                        SemanticField(field_name="chapterTitle"),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=name, fields=fields, vector_search=vector_search, semantic_search=semantic
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--create-if-missing", action="store_true")
    p.add_argument("--batch-size", type=int, default=1000)
    args = p.parse_args()

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    cred = AzureKeyCredential(key)

    if args.create_if_missing:
        idx_client = SearchIndexClient(endpoint, cred)
        existing = {i.name for i in idx_client.list_indexes()}
        if args.index not in existing:
            idx_client.create_index(build_index(args.index))
            print(f"created index: {args.index}")
        else:
            print(f"index already exists: {args.index}")

    client = SearchClient(endpoint, args.index, cred)

    in_path = Path(args.input)
    batch: list[dict] = []
    total = 0
    with in_path.open(encoding="utf-8") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r.setdefault("@search.action", "mergeOrUpload")
            batch.append(r)
            if len(batch) >= args.batch_size:
                client.upload_documents(documents=batch)
                total += len(batch)
                print(f"  uploaded {total}")
                batch = []
    if batch:
        client.upload_documents(documents=batch)
        total += len(batch)

    print(f"uploaded {total} documents to {args.index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
