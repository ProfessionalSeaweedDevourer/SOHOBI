#!/usr/bin/env bash
# 구 Storage Account blob container → 신규 Storage Account blob container 동기화.
#
# 구 환경: sohobi9638logs (별도 sub) — sohobi-logs container (backend 로그)
# 신규 환경: sohobiprodlogs (sub eba83124) — sohobi-logs container
#
# 사전 1회 풀 sync + cutover 시 마지막 증분 sync 2회 실행 패턴.
# delete-destination=false 로 신규 환경 의도치 않은 삭제 방지.
#
# 의존: azcopy 10+ (brew install azcopy)
# 인증: AAD (az login + azcopy login) — Storage Account Key 없이 OAuth 사용
#
# 사용:
#   bash scripts/migrate/08_blob_sync.sh \
#     --src-account sohobi9638logs --src-container sohobi-logs \
#     --dst-account sohobiprodlogs --dst-container sohobi-logs
set -euo pipefail

SRC_ACCOUNT=""
SRC_CONTAINER="sohobi-logs"
DST_ACCOUNT="sohobiprodlogs"
DST_CONTAINER="sohobi-logs"
RECURSIVE="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-account) SRC_ACCOUNT="$2"; shift 2 ;;
    --src-container) SRC_CONTAINER="$2"; shift 2 ;;
    --dst-account) DST_ACCOUNT="$2"; shift 2 ;;
    --dst-container) DST_CONTAINER="$2"; shift 2 ;;
    --no-recursive) RECURSIVE="false"; shift ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SRC_ACCOUNT" ]]; then
  echo "FATAL: --src-account 필수 (구 환경 Storage Account 이름)" >&2
  exit 1
fi

if ! command -v azcopy >/dev/null 2>&1; then
  echo "FATAL: azcopy not found. Install:" >&2
  echo "  brew install azcopy" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$REPO_ROOT/backups/blob-sync/$TS"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/azcopy.log"

SRC_URL="https://${SRC_ACCOUNT}.blob.core.windows.net/${SRC_CONTAINER}"
DST_URL="https://${DST_ACCOUNT}.blob.core.windows.net/${DST_CONTAINER}"

echo "source:      $SRC_URL"
echo "destination: $DST_URL"
echo "recursive:   $RECURSIVE"
echo "log:         $LOG_FILE"
echo ""
echo "사전 확인:"
echo "  1. az login 완료 — Storage Blob Data Reader (source) + Contributor (destination) 권한 보유"
echo "  2. azcopy login (--auth-mode oauth) 완료"
echo ""

# azcopy sync — delete-destination=false 로 신규 측 의도치 않은 삭제 방지
azcopy sync \
  "$SRC_URL" "$DST_URL" \
  --recursive="$RECURSIVE" \
  --delete-destination=false \
  --log-level=INFO \
  2>&1 | tee "$LOG_FILE"

ec=${PIPESTATUS[0]}
if [[ $ec -ne 0 ]]; then
  echo "FAIL — exit $ec, see $LOG_FILE" >&2
  exit "$ec"
fi

echo ""
echo "✓ blob sync 완료"
