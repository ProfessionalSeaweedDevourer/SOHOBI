"""
Railway 로그 + Azure Blob 로그 통합 스크립트

사용법:
  python scripts/merge_logs.py                    # 로컬 logs/ 에만 저장
  python scripts/merge_logs.py --upload           # 로컬 저장 + Blob Storage 업로드
  python scripts/merge_logs.py --remote logs/remote --local logs
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

LOG_TYPES = ("queries", "rejections", "errors")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _read_blob(account: str, log_type: str) -> list[dict]:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError

        container = os.environ.get("BLOB_LOGS_CONTAINER", "sohobi-logs")
        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        blob_client = service.get_blob_client(container=container, blob=f"{log_type}.jsonl")
        text = blob_client.download_blob().readall().decode("utf-8")
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except Exception as e:
        print(f"  Blob 읽기 실패 [{log_type}]: {e}", file=sys.stderr)
        return []


def _upload_blob(account: str, log_type: str, entries: list[dict]) -> None:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobClient, BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError

        container = os.environ.get("BLOB_LOGS_CONTAINER", "sohobi-logs")
        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        blob_client = service.get_blob_client(container=container, blob=f"{log_type}.jsonl")
        content = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"

        # 기존 Append Blob 삭제 후 재생성 (logger가 이어서 append할 수 있도록)
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
        blob_client.create_append_blob()
        blob_client.append_block(content.encode("utf-8"))
        print(f"  Blob 업로드 완료 [{log_type}] ({len(entries)}건)")
    except Exception as e:
        print(f"  Blob 업로드 실패 [{log_type}]: {e}", file=sys.stderr)


def _dedup_key(entry: dict, log_type: str) -> str:
    """중복 제거 키: request_id 우선, 없으면 ts+question 해시"""
    if rid := entry.get("request_id"):
        return rid
    return f"{entry.get('ts', '')}|{entry.get('question', '')}|{entry.get('error', '')}"


def merge(remote_dir: Path, local_dir: Path, upload: bool) -> None:
    blob_account = os.environ.get("BLOB_LOGS_ACCOUNT", "")

    for log_type in LOG_TYPES:
        print(f"\n[{log_type}]")

        # 1. Railway 로그
        remote_entries = _read_jsonl(remote_dir / f"{log_type}.jsonl")
        print(f"  Railway: {len(remote_entries)}건")

        # 2. Azure Blob 로그 (있으면 우선) 또는 로컬
        if blob_account:
            azure_entries = _read_blob(blob_account, log_type)
            print(f"  Azure Blob: {len(azure_entries)}건")
        else:
            azure_entries = _read_jsonl(local_dir / f"{log_type}.jsonl")
            print(f"  로컬 logs/: {len(azure_entries)}건")

        # 3. 머지 & 중복 제거 (Azure 우선: 동일 request_id면 Azure 값 유지)
        merged: dict[str, dict] = {}
        for entry in remote_entries:
            key = _dedup_key(entry, log_type)
            merged[key] = entry
        for entry in azure_entries:
            key = _dedup_key(entry, log_type)
            merged[key] = entry  # Azure가 Railway를 덮어씀

        # 4. ts 기준 오름차순 정렬
        result = sorted(merged.values(), key=lambda e: e.get("ts", ""))

        before = len(remote_entries) + len(azure_entries)
        dedup_count = before - len(result)
        print(f"  머지 결과: {len(result)}건 (중복 제거 {dedup_count}건)")

        # 5. 로컬 저장
        out_path = local_dir / f"{log_type}.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for entry in result:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"  로컬 저장: {out_path}")

        # 6. Blob 업로드 (옵션)
        if upload and blob_account:
            _upload_blob(blob_account, log_type, result)
        elif upload and not blob_account:
            print("  BLOB_LOGS_ACCOUNT 미설정 — Blob 업로드 건너뜀")


def main() -> None:
    parser = argparse.ArgumentParser(description="Railway + Azure 로그 통합")
    parser.add_argument(
        "--remote",
        default="logs/remote",
        help="Railway 로그 디렉터리 (기본값: logs/remote)",
    )
    parser.add_argument(
        "--local",
        default="logs",
        help="Azure/로컬 로그 디렉터리 (기본값: logs)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="머지 결과를 Azure Blob Storage에 업로드",
    )
    args = parser.parse_args()

    remote_dir = Path(args.remote)
    local_dir = Path(args.local)

    if not remote_dir.exists():
        print(f"오류: Railway 로그 디렉터리가 없습니다: {remote_dir}")
        print("먼저 `python scripts/pull_logs.py` 를 실행하십시오.")
        sys.exit(1)

    print(f"Railway 소스: {remote_dir}/")
    print(f"Azure/로컬 소스: {local_dir}/")
    if args.upload:
        account = os.environ.get("BLOB_LOGS_ACCOUNT", "(미설정)")
        print(f"Blob 업로드: 활성화 (계정: {account})")

    merge(remote_dir, local_dir, upload=args.upload)

    print("\n완료. 확인하려면:")
    print("  python log_formatter.py --type queries")


if __name__ == "__main__":
    main()
