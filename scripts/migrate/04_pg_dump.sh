#!/usr/bin/env bash
# PostgreSQL Flexible (위치/상권 DB) → 로컬 dump.
# 사전 dump (D-7~D-1) + cutover 시 마지막 dump 동일 명령으로 재실행.
#
# 의존: pg_dump (16+). 미설치 시: brew install postgresql@16 && brew link --force postgresql@16
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "FATAL: pg_dump not found. Install:" >&2
  echo "  brew install postgresql@16 && brew link --force postgresql@16" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FATAL: $ENV_FILE not found" >&2
  exit 1
fi

# .env 로드 (export)
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
OUT_DIR="$REPO_ROOT/backups/pg/$TS"
mkdir -p "$OUT_DIR"

OUT_FILE="$OUT_DIR/${PG_DB}.dump"
echo "host:     $PG_HOST"
echo "database: $PG_DB"
echo "user:     $PG_USER"
echo "output:   $OUT_FILE"

# custom format(-Fc), 압축 9, 병렬 4 — Azure flexible standard 안전 범위
PGPASSWORD="$PG_PASSWORD" pg_dump \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  --format=custom --compress=9 \
  --no-owner --no-privileges --verbose \
  --file="$OUT_FILE" \
  "sslmode=$PG_SSLMODE" 2> "$OUT_DIR/pg_dump.log" || {
    echo "FAIL — see $OUT_DIR/pg_dump.log" >&2
    tail -20 "$OUT_DIR/pg_dump.log" >&2
    exit 1
  }

# row count 스냅샷 (cutover 후 검증용)
PGPASSWORD="$PG_PASSWORD" psql \
  --host="$PG_HOST" --port="$PG_PORT" \
  --username="$PG_USER" --dbname="$PG_DB" \
  -c "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" \
  -t -A -F$'\t' \
  > "$OUT_DIR/row_counts.tsv" 2>/dev/null || echo "row_counts 수집 실패 (psql 미설치?)"

ls -lh "$OUT_FILE"
echo "✓ dump 완료: $OUT_FILE"
