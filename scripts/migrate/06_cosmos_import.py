#!/usr/bin/env python3
"""Cosmos DB JSONL.gz → 신규 Cosmos 컨테이너 upsert.

02_cosmos_export.py가 만든 backups/cosmos/<ts>/<container>.jsonl.gz 파일 셋을
신규 Cosmos 계정에 부어 넣는다. 멱등(upsert by id) — 동일 입력 재실행 안전.

환경변수: COSMOS_ENDPOINT (target), COSMOS_DATABASE (default sohobi)
        COSMOS_KEY가 있으면 local key 사용, 없으면 AAD 폴백 (신규 cosmos는 AAD 전용)

cutover 전 사전 import + cutover 시 --since 증분 import 2회 실행 패턴.
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


def load_env() -> None:
    env_file = REPO_ROOT / "backend" / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
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
        "  Use: backend/.venv/bin/python3 scripts/migrate/06_cosmos_import.py ...",
        file=sys.stderr,
    )
    sys.exit(1)


def make_client(endpoint: str, key: str | None) -> CosmosClient:
    """Local key 우선, 401(Local Auth disabled) 시 AAD 폴백."""
    if key:
        try:
            client = CosmosClient(endpoint, credential=key)
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


DEFAULT_CONTAINERS = [
    "sessions",
    "roadmap_votes",
    "checklist",
    "feedback",
    "users",
    "usage_events",
]


def import_container(
    client,
    db_name: str,
    container_name: str,
    src_file: Path,
    dry_run: bool,
) -> dict:
    db = client.get_database_client(db_name)
    container = db.get_container_client(container_name)

    n_total = 0
    n_ok = 0
    n_fail = 0
    failures: list[str] = []

    open_fn = gzip.open if src_file.suffix == ".gz" else open
    with open_fn(src_file, "rt", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            try:
                doc = json.loads(line)
            except json.JSONDecodeError as e:
                n_fail += 1
                failures.append(f"line {n_total}: invalid JSON ({e})")
                continue

            # Cosmos 내부 메타필드 제거 (export 시 포함된 _rid/_self/_etag/_attachments/_ts는 upsert가 다시 채움)
            for meta in ("_rid", "_self", "_etag", "_attachments", "_ts"):
                doc.pop(meta, None)

            if dry_run:
                n_ok += 1
                continue

            try:
                container.upsert_item(doc)
                n_ok += 1
            except CosmosHttpResponseError as e:
                n_fail += 1
                failures.append(
                    f"id={doc.get('id', '<no-id>')} status={e.status_code} {e.message[:120]}"
                )

    return {
        "container": container_name,
        "total": n_total,
        "upserted": n_ok,
        "failed": n_fail,
        "failures": failures[:20],  # 첫 20건만 보고
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--in",
        dest="src_dir",
        required=True,
        help="02_cosmos_export.py 출력 디렉토리 (예: backups/cosmos/20260430-020000/)",
    )
    p.add_argument("--containers", nargs="+", default=DEFAULT_CONTAINERS)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 upsert 없이 row count + JSON 검증만",
    )
    args = p.parse_args()

    endpoint = os.environ.get("COSMOS_ENDPOINT")
    key = os.environ.get("COSMOS_KEY") or None
    db_name = os.environ.get("COSMOS_DATABASE", "sohobi")
    if not endpoint:
        print("FATAL: COSMOS_ENDPOINT 누락 (backend/.env 확인)", file=sys.stderr)
        return 1

    src_dir = Path(args.src_dir)
    if not src_dir.is_dir():
        print(f"FATAL: 입력 디렉토리 없음 — {src_dir}", file=sys.stderr)
        return 1

    print(f"target endpoint: {endpoint}")
    print(f"target database: {db_name}")
    print(f"source dir:      {src_dir}")
    if args.dry_run:
        print("** DRY RUN — upsert 미실행 **")

    client = make_client(endpoint, key)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    summary = {
        "endpoint": endpoint,
        "database": db_name,
        "imported_at": ts,
        "dry_run": args.dry_run,
        "containers": [],
    }

    for name in args.containers:
        candidate_files = [
            src_dir / f"{name}.jsonl.gz",
            src_dir / f"{name}.jsonl",
        ]
        src = next((f for f in candidate_files if f.exists()), None)
        if src is None:
            print(f"  {name}: SKIP — 입력 파일 없음")
            summary["containers"].append({"container": name, "skipped": True})
            continue

        result = import_container(client, db_name, name, src, args.dry_run)
        msg = f"  {name}: {result['upserted']}/{result['total']} upserted"
        if result["failed"]:
            msg += f" — {result['failed']} 실패"
        print(msg)
        summary["containers"].append(result)

    out_path = src_dir / f"import-summary-{ts}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n✓ summary -> {out_path}")

    total_failed = sum(c.get("failed", 0) for c in summary["containers"])
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
