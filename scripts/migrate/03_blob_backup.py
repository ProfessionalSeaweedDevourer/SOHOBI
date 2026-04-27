#!/usr/bin/env python3
"""Blob Storage (sohobi9638logs) → 로컬 백업.

azcopy 미설치 환경 대응. AAD(DefaultAzureCredential) 또는 connection string 둘 다 지원.

환경변수:
  BLOB_LOGS_ACCOUNT (필수)
  BLOB_LOGS_CONTAINER (기본: sohobi-logs)
  AZURE_STORAGE_CONNECTION_STRING (선택, 우선 사용)

출력: backups/blob/<timestamp>/<container>/<blob_name>
"""

from __future__ import annotations

import argparse
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
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    print("ERROR: azure-storage-blob/azure-identity not installed.", file=sys.stderr)
    print(
        "  Use: backend/.venv/bin/python3 scripts/migrate/03_blob_backup.py ...",
        file=sys.stderr,
    )
    sys.exit(1)


def make_client(account: str) -> BlobServiceClient:
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)
    url = f"https://{account}.blob.core.windows.net"
    return BlobServiceClient(account_url=url, credential=DefaultAzureCredential())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--account", default=None, help="기본: $BLOB_LOGS_ACCOUNT")
    p.add_argument(
        "--container", default=None, help="기본: $BLOB_LOGS_CONTAINER 또는 sohobi-logs"
    )
    p.add_argument("--out-dir", default=None, help="기본: backups/blob/<timestamp>/")
    args = p.parse_args()

    account = args.account or os.environ.get("BLOB_LOGS_ACCOUNT")
    container = args.container or os.environ.get("BLOB_LOGS_CONTAINER", "sohobi-logs")
    if not account:
        print("FATAL: BLOB_LOGS_ACCOUNT 미설정", file=sys.stderr)
        return 1

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else REPO_ROOT / "backups" / "blob" / ts / container
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    client = make_client(account)
    cont = client.get_container_client(container)

    print(f"account:   {account}")
    print(f"container: {container}")
    print(f"output:    {out_dir}")

    summary = {
        "account": account,
        "container": container,
        "exported_at": ts,
        "blobs": [],
    }
    total_bytes = 0
    for blob in cont.list_blobs():
        local = out_dir / blob.name
        local.parent.mkdir(parents=True, exist_ok=True)
        downloader = cont.get_blob_client(blob.name).download_blob()
        with local.open("wb") as fp:
            for chunk in downloader.chunks():
                fp.write(chunk)
        size = local.stat().st_size
        total_bytes += size
        summary["blobs"].append(
            {
                "name": blob.name,
                "size": size,
                "local": str(local.relative_to(REPO_ROOT)),
            }
        )
        print(f"  {blob.name}: {size:,} bytes")

    summary["total_bytes"] = total_bytes
    (out_dir.parent / f"summary-{ts}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(f"\n✓ {len(summary['blobs'])} blobs, {total_bytes:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
