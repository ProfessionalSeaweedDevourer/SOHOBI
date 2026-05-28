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
    for lineno, raw in enumerate(env_file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            # 형식이 깨진 라인은 silent skip 하지 않고 명시 경고 (멀티라인 secret, CRLF 등 검출)
            print(
                f"WARN: backend/.env line {lineno}: '=' 미포함, skip", file=sys.stderr
            )
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
    """Local key 우선, 'Local Authorization is disabled' 명시 시에만 AAD 폴백.

    이전에는 status 401 도 무조건 폴백했으나, key 만료·IP 차단 등 다른 401 에서 잘못된 인증 경로로 silent
    전환되는 위험이 있어 message 기반 정확 매칭으로 좁힘.
    """
    if key:
        try:
            client = CosmosClient(endpoint, credential=key)
            list(client.list_databases())
            return client
        except CosmosHttpResponseError as e:
            if "Local Authorization is disabled" not in str(e):
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
    failures_dir: Path,
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

    # 사후 검증: target 컨테이너 실제 item count 와 입력 라인 수 대조 (silent drop 검출)
    target_count: int | None = None
    if not dry_run:
        try:
            count_result = list(
                container.query_items(
                    "SELECT VALUE COUNT(1) FROM c",
                    enable_cross_partition_query=True,
                )
            )
            target_count = int(count_result[0]) if count_result else 0
        except CosmosHttpResponseError as e:
            failures.append(
                f"target count query failed: {e.status_code} {e.message[:120]}"
            )

    # failures 전체를 별도 파일로 dump (21번째부터 영구 소실 방지)
    failures_file: str | None = None
    if failures:
        failures_dir.mkdir(parents=True, exist_ok=True)
        failures_file = str(failures_dir / f"failures-{container_name}.jsonl")
        with open(failures_file, "w", encoding="utf-8") as fp:
            for f in failures:
                fp.write(json.dumps({"detail": f}, ensure_ascii=False) + "\n")

    return {
        "container": container_name,
        "total": n_total,
        "upserted": n_ok,
        "failed": n_fail,
        "target_count": target_count,
        "failures_sample": failures[:20],
        "failures_file": failures_file,
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
    print(f"target database: {db_name}  (env COSMOS_DATABASE로 override)")
    print(f"source dir:      {src_dir}")
    if args.dry_run:
        print("** DRY RUN — upsert 미실행 **")

    client = make_client(endpoint, key)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    failures_dir = src_dir / f"import-failures-{ts}"
    summary = {
        "endpoint": endpoint,
        "database": db_name,
        "imported_at": ts,
        "dry_run": args.dry_run,
        "containers": [],
    }

    def write_summary() -> None:
        out_path = src_dir / f"import-summary-{ts}.json"
        try:
            out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"\n✓ summary -> {out_path}")
        except OSError as e:
            print(f"WARN: summary 파일 쓰기 실패 ({e}) — stdout 출력", file=sys.stderr)
            print(json.dumps(summary, ensure_ascii=False, indent=2))

    try:
        for name in args.containers:
            candidate_files = [
                src_dir / f"{name}.jsonl.gz",
                src_dir / f"{name}.jsonl",
            ]
            src = next((f for f in candidate_files if f.exists()), None)
            if src is None:
                print(f"  {name}: SKIP — 입력 파일 없음")
                # SKIP 도 실패로 간주 (total_failed 에 합산되어 exit code 1)
                summary["containers"].append(
                    {"container": name, "skipped": True, "reason": "input file missing"}
                )
                continue

            try:
                result = import_container(
                    client, db_name, name, src, args.dry_run, failures_dir
                )
            except Exception as e:
                # 한 컨테이너 실패 시 partial summary 보전을 위해 catch 후 다음 컨테이너 진행
                print(f"  {name}: FAIL — {type(e).__name__}: {e}", file=sys.stderr)
                summary["containers"].append(
                    {
                        "container": name,
                        "error": f"{type(e).__name__}: {str(e)[:200]}",
                    }
                )
                continue

            msg = f"  {name}: {result['upserted']}/{result['total']} upserted"
            if result["failed"]:
                msg += f" — {result['failed']} 실패"
            if (
                result["target_count"] is not None
                and result["target_count"] != result["total"]
            ):
                msg += f" — target count mismatch (got {result['target_count']}, expected ≥ {result['total']})"
            print(msg)
            summary["containers"].append(result)
    finally:
        write_summary()

    # SKIP·error·failed·target count mismatch 모두 실패로 집계
    has_failure = False
    for c in summary["containers"]:
        if c.get("skipped") or c.get("error") or c.get("failed", 0) > 0:
            has_failure = True
            break
        tc = c.get("target_count")
        if tc is not None and tc < c.get("total", 0):
            has_failure = True
            break

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
