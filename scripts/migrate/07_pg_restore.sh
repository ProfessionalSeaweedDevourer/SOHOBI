#!/usr/bin/env bash
# pg_dump (--format=custom) → 신규 PG flexible 서버로 restore.
# 04_pg_dump.sh 산출물을 입력으로 받는다. 멱등(--clean --if-exists)으로 재실행 안전.
#
# 환경변수: backend/.env에서 PG_HOST/PG_DB/PG_USER/PG_PASSWORD 로드.
# 신규 환경으로 restore하려면 먼저 .env를 신규 PG 정보로 갱신 후 실행.
#
# 사용:
#   bash scripts/migrate/07_pg_restore.sh <dump-file> [--jobs N] [--schema-only|--data-only] [--dry-run]
#
# --dry-run: pg_restore --list 로 dump 내용만 표시 (DROP·재생성 미수행). cutover 직전 안전 확인용.
#
# 의존: pg_restore + psql (postgresql@16+)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

if [[ $# -lt 1 ]]; then
  echo "사용: $0 <dump-file> [--jobs N] [--schema-only|--data-only] [--dry-run]" >&2
  exit 1
fi

DUMP_FILE="$1"; shift
JOBS=1
DRY_RUN=false
SCHEMA_ONLY=false
DATA_ONLY=false
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jobs) JOBS="$2"; shift 2 ;;
    --schema-only) SCHEMA_ONLY=true; EXTRA_FLAGS+=("--schema-only"); shift ;;
    --data-only) DATA_ONLY=true; EXTRA_FLAGS+=("--data-only"); shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
  esac
done

if [[ "$SCHEMA_ONLY" == "true" && "$DATA_ONLY" == "true" ]]; then
  echo "FATAL: --schema-only 와 --data-only 는 동시 사용 불가" >&2
  exit 1
fi

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "FATAL: dump 파일 없음 — $DUMP_FILE" >&2
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "FATAL: pg_restore not found. Install:" >&2
  echo "  brew install postgresql@16 && brew link --force postgresql@16" >&2
  exit 1
fi

# --dry-run: PG 접속 없이 dump 내용만 표시
if [[ "$DRY_RUN" == "true" ]]; then
  echo "** DRY RUN: pg_restore --list 결과 (DROP·재생성 미수행) **"
  echo ""
  pg_restore --list "$DUMP_FILE"
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FATAL: $ENV_FILE not found" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${PG_HOST:?PG_HOST 누락}"
: "${PG_PORT:=5432}"
: "${PG_DB:?PG_DB 누락}"
: "${PG_USER:?PG_USER 누락}"
: "${PG_PASSWORD:?PG_PASSWORD 누락}"
# sslmode 는 환경변수 PGSSLMODE 로 전달 (위치 인자로 넘기면 pg_restore 가 dump 파일로 오해)
export PGSSLMODE="${PG_SSLMODE:-require}"
export PGPASSWORD="$PG_PASSWORD"

TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$REPO_ROOT/backups/pg-restore/$TS"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pg_restore.log"

echo "target host:     $PG_HOST"
echo "target database: $PG_DB"
echo "target user:     $PG_USER"
echo "sslmode:         $PGSSLMODE"
echo "dump file:       $DUMP_FILE"
echo "jobs:            $JOBS"
echo "extra flags:     ${EXTRA_FLAGS[*]:-(none)}"
echo "log:             $LOG_FILE"
echo ""

# 사전 점검: 신규 DB 접근 가능 + db 존재
psql \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  -c "SELECT version();" \
  > "$LOG_DIR/preflight.log" 2>&1 || {
    echo "FAIL — 신규 PG 접속 실패. log: $LOG_DIR/preflight.log" >&2
    cat "$LOG_DIR/preflight.log" >&2
    exit 1
  }

START="$(date +%s)"

# --exit-on-error: 개별 SQL 실패 시 즉시 중단 (기본은 warning 출력 후 계속 — silent 부분 실패 위험)
pg_restore \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  --no-owner --no-privileges \
  --clean --if-exists \
  --exit-on-error \
  --jobs="$JOBS" \
  --verbose \
  "${EXTRA_FLAGS[@]}" \
  "$DUMP_FILE" \
  2> "$LOG_FILE" || {
    echo "FAIL — see $LOG_FILE" >&2
    tail -30 "$LOG_FILE" >&2
    exit 1
  }

ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "✓ restore 완료 (${ELAPSED}s)"

# row count 검증 (사후 비교용). 실패 시 명시적 exit — 사후 검증 자료 손실 silent 방지
psql \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  -c "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" \
  -t -A -F$'\t' \
  > "$LOG_DIR/row_counts.tsv" || {
    echo "FAIL — row_counts 수집 실패. log: $LOG_DIR/row_counts.tsv" >&2
    exit 1
  }

echo "row counts -> $LOG_DIR/row_counts.tsv"
