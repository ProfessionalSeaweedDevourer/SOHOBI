#!/usr/bin/env python3
"""현 AI Search 인덱스 schema·document count 백업.

기획안 §AI Search 재빌드 → 인덱스 자체는 source 재빌드하지만, 현재 schema/synonym/scoring profile은
신규 v2 설계 시 참조. 추후 비교용으로 보존.

대상: legal-index (AZURE_SEARCH_*), gov-programs-index (GOV_SEARCH_*)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "backend" / ".env"


def load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
except ImportError:
    print("ERROR: azure-search-documents not installed.", file=sys.stderr)
    sys.exit(1)


def export_index(endpoint: str, key: str, index_name: str, out_dir: Path) -> dict:
    cred = AzureKeyCredential(key)
    idx_client = SearchIndexClient(endpoint, cred)
    search_client = SearchClient(endpoint, index_name, cred)

    out_dir.mkdir(parents=True, exist_ok=True)
    info: dict = {"endpoint": endpoint, "index": index_name}

    try:
        index = idx_client.get_index(index_name)
        # azure SDK 객체 → dict (직렬화 가능 형태로)
        schema = index.serialize() if hasattr(index, "serialize") else index.as_dict()
        (out_dir / f"{index_name}.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, default=str)
        )
        info["schema_file"] = f"{index_name}.schema.json"
        info["fields"] = [f.name for f in index.fields]
    except Exception as e:
        info["schema_error"] = str(e)

    try:
        info["document_count"] = search_client.get_document_count()
    except Exception as e:
        info["count_error"] = str(e)

    try:
        # synonym map (있으면)
        syn_maps = list(idx_client.list_synonym_maps())
        info["synonym_maps"] = [s.name for s in syn_maps]
        for s in syn_maps:
            (out_dir / f"synonym_{s.name}.json").write_text(
                json.dumps(
                    {"name": s.name, "synonyms": s.synonyms},
                    ensure_ascii=False,
                    indent=2,
                )
            )
    except Exception as e:
        info["synonym_error"] = str(e)

    return info


def main() -> int:
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = REPO_ROOT / "backups" / "search-schema" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = []
    if os.environ.get("AZURE_SEARCH_ENDPOINT") and os.environ.get("AZURE_SEARCH_KEY"):
        targets.append(
            (
                "legal",
                os.environ["AZURE_SEARCH_ENDPOINT"],
                os.environ["AZURE_SEARCH_KEY"],
                os.environ.get("AZURE_SEARCH_INDEX", "legal-index"),
            )
        )
    if os.environ.get("GOV_SEARCH_ENDPOINT") and os.environ.get("GOV_SEARCH_API_KEY"):
        targets.append(
            (
                "gov",
                os.environ["GOV_SEARCH_ENDPOINT"],
                os.environ["GOV_SEARCH_API_KEY"],
                os.environ.get("GOV_SEARCH_INDEX_NAME", "gov-programs-index"),
            )
        )

    if not targets:
        print(
            "FATAL: 환경변수 누락 — AZURE_SEARCH_* 또는 GOV_SEARCH_* 필요",
            file=sys.stderr,
        )
        return 1

    summary = {"exported_at": ts, "targets": []}
    for label, endpoint, key, idx in targets:
        sub_dir = out_dir / label
        info = export_index(endpoint, key, idx, sub_dir)
        info["label"] = label
        summary["targets"].append(info)
        print(f"[{label}] {endpoint} / {idx}")
        print(f"  document_count: {info.get('document_count', 'ERR')}")
        print(f"  fields: {len(info.get('fields', []))}")

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(f"\n✓ {out_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
