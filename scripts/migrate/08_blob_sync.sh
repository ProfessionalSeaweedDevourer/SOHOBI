#!/usr/bin/env bash
# 구 Storage Account blob container → 신규 Storage Account blob container 동기화.
#
# 구 환경: sohobi9638logs (별도 sub) — sohobi-logs container (backend 로그)
# 신규 환경: sohobiprodlogs (sub eba83124) — sohobi-logs container
#
# 사전 1회 풀 sync + cutover 시 마지막 증분 sync 2회 실행 패턴.
# delete-destination=false 로 신규 환경 의도치 않은 삭제 방지.
#
# 의존: azcopy 10+ (brew install azcopy), az CLI
# 인증: AAD (az login + azcopy login) — Storage Account Key 없이 OAuth 사용
#
# 사용:
#   bash scripts/migrate/08_blob_sync.sh \
#     --src-account sohobi9638logs --src-container sohobi-logs \
#     --dst-account sohobiprodlogs --dst-container sohobi-logs \
#     [--dry-run]
set -euo pipefail

SRC_ACCOUNT=""
SRC_CONTAINER="sohobi-logs"
DST_ACCOUNT="sohobiprodlogs"
DST_CONTAINER="sohobi-logs"
RECURSIVE="true"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-account) SRC_ACCOUNT="$2"; shift 2 ;;
    --src-container) SRC_CONTAINER="$2"; shift 2 ;;
    --dst-account) DST_ACCOUNT="$2"; shift 2 ;;
    --dst-container) DST_CONTAINER="$2"; shift 2 ;;
    --no-recursive) RECURSIVE="false"; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
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

# OAuth 토큰 사전 점검 — 만료된 상태에서 실행 시 azcopy 가 403 으로 부분 실패 후 silent 통과 가능
if ! azcopy login status >/dev/null 2>&1; then
  echo "FATAL: azcopy login 필요. 다음 명령 실행 후 재시도:" >&2
  echo "  az login" >&2
  echo "  azcopy login --auth-mode oauth" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$REPO_ROOT/backups/blob-sync/$TS"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/azcopy.log"
VERIFY_FILE="$LOG_DIR/verify.txt"

SRC_URL="https://${SRC_ACCOUNT}.blob.core.windows.net/${SRC_CONTAINER}"
DST_URL="https://${DST_ACCOUNT}.blob.core.windows.net/${DST_CONTAINER}"

echo "source:      $SRC_URL"
echo "destination: $DST_URL"
echo "recursive:   $RECURSIVE"
echo "dry-run:     $DRY_RUN"
echo "log:         $LOG_FILE"
echo ""
echo "사전 확인:"
echo "  1. az login 완료 — Storage Blob Data Reader (source) + Contributor (destination) 권한 보유"
echo "  2. azcopy login (--auth-mode oauth) 완료"
echo ""

# azcopy sync — delete-destination=false 로 신규 측 의도치 않은 삭제 방지
AZCOPY_FLAGS=(
  --recursive="$RECURSIVE"
  --delete-destination=false
  --log-level=INFO
)
if [[ "$DRY_RUN" == "true" ]]; then
  AZCOPY_FLAGS+=(--dry-run)
fi

azcopy sync \
  "$SRC_URL" "$DST_URL" \
  "${AZCOPY_FLAGS[@]}" \
  2>&1 | tee "$LOG_FILE"

ec=${PIPESTATUS[0]}
if [[ $ec -ne 0 ]]; then
  echo "FAIL — exit $ec, see $LOG_FILE" >&2
  exit "$ec"
fi

# azcopy 는 partial 실패(403, 5xx, retry exhausted)에서도 exit 0 가능 — summary 의 Failed 카운트 명시 검증
FAILED_COUNT=$(grep -E "Number of (File )?Transfers Failed\s*:\s*[0-9]+" "$LOG_FILE" \
  | grep -oE "[0-9]+$" | head -1 || echo "0")
if [[ -n "$FAILED_COUNT" && "$FAILED_COUNT" -gt 0 ]]; then
  echo "FAIL — azcopy summary 에 Failed Transfers ${FAILED_COUNT} 건 (silent partial failure)" >&2
  echo "  see: $LOG_FILE" >&2
  exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
  echo ""
  echo "✓ DRY RUN 완료 — 실제 동기화 미수행"
  exit 0
fi

# 사후 검증: source vs destination object count 대조 (cutover 직전 신규 write 누락 검출)
echo ""
echo "사후 검증 (source vs destination object count):"

SRC_COUNT=$(az storage blob list \
  --account-name "$SRC_ACCOUNT" --container-name "$SRC_CONTAINER" \
  --auth-mode login --num-results "*" --query "length(@)" -o tsv 2>/dev/null || echo "?")
DST_COUNT=$(az storage blob list \
  --account-name "$DST_ACCOUNT" --container-name "$DST_CONTAINER" \
  --auth-mode login --num-results "*" --query "length(@)" -o tsv 2>/dev/null || echo "?")

{
  echo "src: $SRC_ACCOUNT/$SRC_CONTAINER = $SRC_COUNT"
  echo "dst: $DST_ACCOUNT/$DST_CONTAINER = $DST_COUNT"
} | tee "$VERIFY_FILE"

if [[ "$SRC_COUNT" == "?" || "$DST_COUNT" == "?" ]]; then
  echo "WARN — count 조회 실패 (권한 또는 네트워크). 수동 검증 권장" >&2
elif [[ "$SRC_COUNT" -ne "$DST_COUNT" ]]; then
  echo "WARN — src($SRC_COUNT) ≠ dst($DST_COUNT). 증분 sync 중이거나 누락 가능. 재실행 또는 수동 확인" >&2
fi

echo ""
echo "✓ blob sync 완료"
