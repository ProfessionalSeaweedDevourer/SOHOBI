#!/usr/bin/env bash
# pg_dump (--format=custom) → 신규 PG flexible 서버로 restore.
# 04_pg_dump.sh 산출물을 입력으로 받는다. 멱등(--clean --if-exists)으로 재실행 안전.
#
# 환경변수: backend/.env에서 PG_HOST/PG_DB/PG_USER/PG_PASSWORD 로드.
# 신규 환경으로 restore하려면 먼저 .env를 신규 PG 정보로 갱신 후 실행.
#
# 사용:
#   bash scripts/migrate/07_pg_restore.sh <dump-file> [--jobs N] [--schema-only|--data-only]
#
# 의존: pg_restore + psql (postgresql@16+)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

if [[ $# -lt 1 ]]; then
  echo "사용: $0 <dump-file> [--jobs N] [--schema-only|--data-only]" >&2
  exit 1
fi

DUMP_FILE="$1"; shift
JOBS=1
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jobs) JOBS="$2"; shift 2 ;;
    --schema-only) EXTRA_FLAGS+=("--schema-only"); shift ;;
    --data-only) EXTRA_FLAGS+=("--data-only"); shift ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "FATAL: dump 파일 없음 — $DUMP_FILE" >&2
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "FATAL: pg_restore not found. Install:" >&2
  echo "  brew install postgresql@16 && brew link --force postgresql@16" >&2
  exit 1
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
PG_SSLMODE="${PG_SSLMODE:-require}"

TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$REPO_ROOT/backups/pg-restore/$TS"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pg_restore.log"

echo "target host:     $PG_HOST"
echo "target database: $PG_DB"
echo "target user:     $PG_USER"
echo "dump file:       $DUMP_FILE"
echo "jobs:            $JOBS"
echo "extra flags:     ${EXTRA_FLAGS[*]:-(none)}"
echo "log:             $LOG_FILE"
echo ""

# 사전 점검: 신규 DB 접근 가능 + db 존재
PGPASSWORD="$PG_PASSWORD" psql \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  -c "SELECT version();" \
  "sslmode=$PG_SSLMODE" > "$LOG_DIR/preflight.log" 2>&1 || {
    echo "FAIL — 신규 PG 접속 실패. log: $LOG_DIR/preflight.log" >&2
    cat "$LOG_DIR/preflight.log" >&2
    exit 1
  }

START="$(date +%s)"

PGPASSWORD="$PG_PASSWORD" pg_restore \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  --no-owner --no-privileges \
  --clean --if-exists \
  --jobs="$JOBS" \
  --verbose \
  "${EXTRA_FLAGS[@]}" \
  "$DUMP_FILE" \
  "sslmode=$PG_SSLMODE" 2> "$LOG_FILE" || {
    echo "FAIL — see $LOG_FILE" >&2
    tail -30 "$LOG_FILE" >&2
    exit 1
  }

ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "✓ restore 완료 (${ELAPSED}s)"

# row count 검증 (사후 비교용)
PGPASSWORD="$PG_PASSWORD" psql \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  -c "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" \
  -t -A -F$'\t' \
  > "$LOG_DIR/row_counts.tsv" 2>/dev/null || echo "row_counts 수집 실패"

echo "row counts -> $LOG_DIR/row_counts.tsv"
