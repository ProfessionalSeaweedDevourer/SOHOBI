"""
Railway 볼륨 로그 → 로컬 동기화 스크립트

사용법:
  python scripts/pull_logs.py                          # .env의 값 자동 사용
  python scripts/pull_logs.py --host https://xxx.up.railway.app
  python scripts/pull_logs.py --type queries           # 특정 타입만
  python scripts/pull_logs.py --out logs/remote/       # 저장 경로 지정

이후 로컬 분석:
  LOGS_DIR=logs/remote python log_formatter.py --type queries
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

LOG_TYPES = ("queries", "rejections", "errors")


def pull(host: str, secret: str, log_type: str, out_dir: Path) -> None:
    url = f"{host.rstrip('/')}/api/v1/logs/export"
    params = {"type": log_type, "key": secret}

    print(f"  [{log_type}] 요청 중... ", end="", flush=True)
    try:
        r = requests.get(url, params=params, timeout=60, stream=True)
        if r.status_code == 403:
            print("실패 — EXPORT_SECRET 불일치")
            sys.exit(1)
        if r.status_code == 404:
            print("건너뜀 (파일 없음)")
            return
        if r.status_code != 200:
            print(f"실패 — HTTP {r.status_code}")
            sys.exit(1)

        out_path = out_dir / f"{log_type}.jsonl"
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

        size_kb = out_path.stat().st_size / 1024
        print(f"완료 → {out_path} ({size_kb:.1f} KB)")
    except requests.ConnectionError:
        print(f"실패 — 서버에 연결할 수 없습니다: {host}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Railway 로그 로컬 동기화")
    parser.add_argument(
        "--host",
        default=os.getenv("RAILWAY_HOST", ""),
        help="Railway 서비스 URL (예: https://xxx.up.railway.app). "
             "환경변수 RAILWAY_HOST로도 설정 가능.",
    )
    parser.add_argument(
        "--secret",
        default=os.getenv("EXPORT_SECRET", ""),
        help="EXPORT_SECRET 값. 미지정 시 .env에서 읽음.",
    )
    parser.add_argument(
        "--type",
        choices=[*LOG_TYPES, "all"],
        default="all",
        help="가져올 로그 타입 (기본값: all)",
    )
    parser.add_argument(
        "--out",
        default="logs/remote",
        help="저장 디렉터리 (기본값: logs/remote)",
    )
    args = parser.parse_args()

    if not args.host:
        print("오류: --host 또는 환경변수 RAILWAY_HOST 를 지정하십시오.")
        sys.exit(1)
    if not args.secret:
        print("오류: --secret 또는 .env의 EXPORT_SECRET 을 설정하십시오.")
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    types = LOG_TYPES if args.type == "all" else (args.type,)
    print(f"대상: {args.host}  →  {out_dir}/")
    for t in types:
        pull(args.host, args.secret, t, out_dir)

    print("\n분석하려면:")
    print(f"  LOGS_DIR={out_dir} python log_formatter.py --type queries")


if __name__ == "__main__":
    main()
