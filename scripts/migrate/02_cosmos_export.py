#!/usr/bin/env python3
"""Cosmos DB 컨테이너 → JSONL.gz export.

기획안 §Phase 0 step 5 — 사전(전량) export, cutover 시 --since로 증분만 재push.

환경변수: backend/.env에서 자동 로드 (COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE)
출력: backups/cosmos/<timestamp>/<container>.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
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
    from azure.cosmos import CosmosClient
    from azure.cosmos.exceptions import CosmosHttpResponseError
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("ERROR: azure-cosmos / azure-identity 미설치.", file=sys.stderr)
    print(
        "  Use: backend/.venv/bin/python3 scripts/migrate/02_cosmos_export.py ...",
        file=sys.stderr,
    )
    sys.exit(1)


def make_client(endpoint: str, key: str | None) -> CosmosClient:
    """Local key 우선, 401(Local Auth disabled) 시 AAD 폴백."""
    if key:
        try:
            client = CosmosClient(endpoint, credential=key)
            # smoke-test: 데이터베이스 목록 호출
            list(client.list_databases())
            return client
        except CosmosHttpResponseError as e:
            if "Local Authorization is disabled" not in str(e) and e.status_code != 401:
                raise
            print(
                "INFO: Local Auth 비활성 — DefaultAzureCredential 폴백",
                file=sys.stderr,
            )
    return CosmosClient(endpoint, credential=DefaultAzureCredential())


# 실측 (2026-04-27 listContainers): sessions, roadmap_votes, checklist, feedback, users, usage_events
DEFAULT_CONTAINERS = [
    "sessions",
    "roadmap_votes",
    "checklist",
    "feedback",
    "users",
    "usage_events",
]


def export_container(
    client, db_name: str, container_name: str, out_path: Path, since_iso: str | None
) -> int:
    db = client.get_database_client(db_name)
    container = db.get_container_client(container_name)

    if since_iso:
        # _ts (epoch sec) 기반 증분. ISO → epoch 변환
        dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        since_epoch = int(dt.timestamp())
        query = f"SELECT * FROM c WHERE c._ts >= {since_epoch}"
        items = container.query_items(query=query, enable_cross_partition_query=True)
    else:
        items = container.read_all_items()

    n = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as fp:
        for item in items:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--containers", nargs="+", default=DEFAULT_CONTAINERS)
    p.add_argument("--out-dir", default=None, help="기본: backups/cosmos/<timestamp>/")
    p.add_argument(
        "--since",
        default=None,
        help="ISO timestamp — 증분 export (e.g., 2026-04-26T00:00:00Z)",
    )
    args = p.parse_args()

    endpoint = os.environ.get("COSMOS_ENDPOINT")
    key = os.environ.get("COSMOS_KEY") or None
    db_name = os.environ.get("COSMOS_DATABASE", "sohobidb")
    if not endpoint:
        print("FATAL: COSMOS_ENDPOINT 누락 (backend/.env 확인)", file=sys.stderr)
        return 1

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = (
        Path(args.out_dir) if args.out_dir else REPO_ROOT / "backups" / "cosmos" / ts
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    client = make_client(endpoint, key)

    print(f"endpoint: {endpoint}")
    print(f"database: {db_name}")
    print(f"output:   {out_dir}")
    if args.since:
        print(f"since:    {args.since} (증분)")

    summary = {"db": db_name, "exported_at": ts, "since": args.since, "containers": {}}
    for name in args.containers:
        out_path = out_dir / f"{name}.jsonl.gz"
        try:
            n = export_container(client, db_name, name, out_path, args.since)
            print(f"  {name}: {n} docs -> {out_path.name}")
            summary["containers"][name] = {"count": n, "file": out_path.name}
        except Exception as e:
            print(f"  {name}: FAILED — {e}", file=sys.stderr)
            summary["containers"][name] = {"error": str(e)}

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(f"\n✓ summary -> {out_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
