#!/usr/bin/env bash
# Azure 마이그레이션 사전 점검 — 신규 구독 발급 전에 실행 가능.
# - az login 상태, 구독·테넌트 식별
# - backend/.env 필수 변수 존재 여부
# - 백업 도구(azcopy/pg_dump) 가용성

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; }

echo "=== az login ==="
if az account show >/dev/null 2>&1; then
  az account show --query "{tenant:tenantId, subscription:name, user:user.name}" -o table
else
  fail "az login 필요 — 'az login' 실행"
  exit 1
fi

echo
echo "=== backend/.env 필수 변수 ==="
if [[ ! -f "$ENV_FILE" ]]; then
  fail ".env 파일 없음: $ENV_FILE"
  exit 1
fi
REQUIRED=(
  COSMOS_ENDPOINT COSMOS_KEY COSMOS_DATABASE
  BLOB_LOGS_ACCOUNT
  PG_HOST PG_PORT PG_DB PG_USER PG_PASSWORD
  AZURE_SEARCH_ENDPOINT AZURE_SEARCH_KEY AZURE_SEARCH_INDEX
  GOV_SEARCH_ENDPOINT GOV_SEARCH_API_KEY GOV_SEARCH_INDEX_NAME
)
missing=()
for var in "${REQUIRED[@]}"; do
  if grep -q "^${var}=" "$ENV_FILE"; then
    ok "$var"
  else
    missing+=("$var")
    fail "$var (누락)"
  fi
done

echo
echo "=== 백업 도구 가용성 ==="
for tool in azcopy pg_dump python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool: $(command -v "$tool")"
  else
    case "$tool" in
      azcopy)   warn "azcopy 미설치 — Python azure-storage-blob 백업으로 대체 가능 (스크립트 03 사용)";;
      pg_dump)  warn "pg_dump 미설치 — 'brew install postgresql@16' 권장";;
      *)        fail "$tool 미설치";;
    esac
  fi
done

echo
echo "=== Python 패키지 (.venv) ==="
VENV_PY="$REPO_ROOT/backend/.venv/bin/python3"
check_pkg() {
  local pkg="$1" import="$2"
  if "$VENV_PY" -c "import $import" 2>/dev/null; then
    ok "$pkg"
  else
    warn "$pkg 미설치 — pip install $pkg"
  fi
}
if [[ -x "$VENV_PY" ]]; then
  check_pkg "azure-cosmos" "azure.cosmos"
  check_pkg "azure-storage-blob" "azure.storage.blob"
  check_pkg "azure-search-documents" "azure.search.documents"
  check_pkg "psycopg2" "psycopg2"
else
  warn "backend/.venv 없음 — python3 -m venv backend/.venv && pip install -r backend/requirements.txt"
fi

echo
if (( ${#missing[@]} > 0 )); then
  fail "필수 .env 변수 누락: ${missing[*]}"
  exit 1
fi
ok "preflight 통과 — 다음 단계 진행 가능"
