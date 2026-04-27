# Azure 테넌트 이전 — 사전 준비 런북

> 관련 기획안: [2026-04-26-azure-tenant-migration.md](../plans/2026-04-26-azure-tenant-migration.md)
>
> 본 런북은 **신규 테넌트·구독 발급 전에 즉시 실행 가능한 준비 작업**만 다룬다. cutover 본 절차는 별도.

## 목적

신규 구독 프로비저닝 일정과 무관하게 **언제든 끊어질 수 있는 기존 환경**의 데이터·구성을 지금 안전하게 외부로 백업해 둔다. 과거 `choiasearchhh` 외부 계정 접근 차단 사고가 재현될 가능성을 차단한다 (실제로 본 작업 중 legal-index 접근이 이미 막혀있음을 확인 — §5 참조).

## 즉시 가능 / 후속 분기

| 항목 | 도구 | 상태 |
|------|------|------|
| ① 환경 sanity check | `bash scripts/migrate/00_preflight.sh` | 즉시 |
| ② 리소스·RBAC 인벤토리 스냅샷 | `bash scripts/migrate/01_snapshot_resources.sh` | 즉시 |
| ③ Cosmos DB 6개 컨테이너 export | `python3 scripts/migrate/02_cosmos_export.py` | 즉시 |
| ④ Blob Storage 로그 백업 | `python3 scripts/migrate/03_blob_backup.py` | 즉시 |
| ⑤ AI Search 스키마 백업 | `python3 scripts/migrate/05_search_schema_export.py` | 즉시 (단 legal은 차단) |
| ⑥ PostgreSQL pg_dump | `bash scripts/migrate/04_pg_dump.sh` | **사전 준비 필요** (§6) |
| ⑦ AI Search 소스 데이터 확보 | 팀원 접촉 | 워크스트림 분리 (별건) |

## 실행 순서

### 1) Preflight

```bash
bash scripts/migrate/00_preflight.sh
```

확인 항목:
- `az login` 상태 (현재 테넌트·구독 ID 기록)
- `backend/.env` 필수 변수 (Cosmos·PG·Blob·AI Search)
- 백업 도구 (azcopy/pg_dump 미설치 시 경고 — 본 런북에서 대체 경로 안내)
- Python 패키지 (azure-cosmos, azure-storage-blob, azure-search-documents, psycopg2)

### 2) 리소스 인벤토리

```bash
bash scripts/migrate/01_snapshot_resources.sh
```

산출물 (`backups/azure-snapshot/<timestamp>/`):
- `resources.json` / `resources.txt` — RG 산하 전 리소스
- `role_assignments.json` — RBAC (신규 구독에서 동일 권한 재구성용)
- `containerapp_*.json` + `_envvars.txt` — Container App 설정 + env 키 목록
- `cosmos_*.json` — Cosmos 계정 설정 + 컨테이너 정의
- `search_*.json` — AI Search service 메타
- `storage_*.json` — Storage account 메타

이 스냅샷이 Bicep IaC 작성 시 역공학 입력이 된다.

### 3) Cosmos DB export (전량)

```bash
backend/.venv/bin/python3 scripts/migrate/02_cosmos_export.py
```

**실측 컨테이너 (2026-04-27)**: `sessions`, `roadmap_votes`, `checklist`(단수), `feedback`, `users`, `usage_events` — 총 6개.

산출물: `backups/cosmos/<timestamp>/<container>.jsonl.gz` + `summary.json`

**주의**: Cosmos 계정에 **Local Auth가 비활성**되어 있다 (스크립트가 401 시 `DefaultAzureCredential`로 자동 폴백). `az login` 사용자에게 Cosmos 데이터 평면 권한이 있어야 한다 — 현재는 `eric.park@miee.dev` Owner 권한으로 동작.

### 4) Blob Storage 로그 백업

```bash
backend/.venv/bin/python3 scripts/migrate/03_blob_backup.py
```

산출물: `backups/blob/<timestamp>/sohobi-logs/{queries,rejections,errors}.jsonl`

azcopy 미설치 환경 대응 — Python SDK로 동등 동작.

### 5) AI Search 스키마 export

```bash
backend/.venv/bin/python3 scripts/migrate/05_search_schema_export.py
```

산출물: `backups/search-schema/<timestamp>/{legal,gov}/<index>.schema.json`

**알려진 제약**: legal-index 호스팅 search service(`choiasearchhh.search.windows.net`)는 **외부 계정 소유 + 접근 차단** 상태. 본 스크립트가 schema·count 모두 ERR로 반환되는 것이 정상. 이 사실 자체가 기획안의 "legal는 소스 재빌드" 결정을 정당화한다 ([2026-04-26-legal-index-rebuild.md](../plans/2026-04-26-legal-index-rebuild.md)).

gov-programs-index(`sohobi-search.search.windows.net`)는 7,019 docs, 22 fields로 정상 export됨.

### 6) PostgreSQL pg_dump (사전 준비 필요)

#### 6-1. pg_dump 설치 (macOS)

```bash
brew install postgresql@16
brew link --force postgresql@16
pg_dump --version  # 16.x 확인
```

#### 6-2. Firewall 임시 허용

PostgreSQL Flexible은 IP allowlist 방식. 로컬 머신에서 접근 불가 상태가 기본 — Container App·Cloud Shell만 허용됨. 현재 공인 IP를 임시로 추가:

```bash
MY_IP=$(curl -s https://api.ipify.org)
echo "공인 IP: $MY_IP"
az postgres flexible-server firewall-rule create \
  --resource-group rg-ejp-9638 \
  --name sohobi-db-prod \
  --rule-name "local-pg-dump-$(date +%Y%m%d)" \
  --start-ip-address "$MY_IP" \
  --end-ip-address "$MY_IP"
```

#### 6-3. dump 실행

```bash
bash scripts/migrate/04_pg_dump.sh
```

산출물: `backups/pg/<timestamp>/{<db>.dump, row_counts.tsv, pg_dump.log}`

custom format(-Fc) + 압축 9 — `pg_restore`로 신규 PG에 그대로 복원 가능.

#### 6-4. Firewall 룰 즉시 제거

dump 완료 후 **반드시** 임시 룰 삭제:

```bash
az postgres flexible-server firewall-rule delete \
  --resource-group rg-ejp-9638 \
  --name sohobi-db-prod \
  --rule-name "local-pg-dump-$(date +%Y%m%d)" \
  --yes
```

### 7) AI Search 소스 데이터 확보 (워크스트림 분리)

기획안의 가장 큰 미확정 변수. 본 런북 범위 외:
- legal-index 재빌드용 원본 PDF/JSON: 보유 팀원 식별 → 공식 요청
- gov-programs-index 재빌드용: 정부지원사업 자동수집 Function App 소스 + 수집 대상 목록 확보
- 부재 시 fallback: 법제처·정부24 OpenAPI 재수집 파이프라인 설계

진척이 본 cutover 일정과 분리되도록 별건 이슈로 추적 권장.

## 검증

### 데이터 무결성 (백업 직후)

```bash
# Cosmos summary 확인
cat backups/cosmos/*/summary.json | python3 -m json.tool

# Blob 파일 크기 확인
ls -lh backups/blob/*/sohobi-logs/

# PG dump 무결성 (pg_restore --list로 schema 확인)
pg_restore --list backups/pg/*/sohobidb.dump | head -20
```

### 백업 실측 (2026-04-27 1차 실행 결과)

| 항목 | 결과 |
|------|------|
| Cosmos sessions | 5 docs |
| Cosmos roadmap_votes | 16 docs |
| Cosmos checklist | 261 docs |
| Cosmos feedback | 16 docs |
| Cosmos users | 5 docs |
| Cosmos usage_events | 3,256 docs |
| **Cosmos 합계** | **3,559 docs** |
| Blob queries.jsonl | 2,360,445 bytes |
| Blob rejections.jsonl | 445,275 bytes |
| Blob errors.jsonl | 72,474 bytes |
| **Blob 합계** | **3 blobs, 2.9 MB** |
| AI Search legal | **ERR (외부 계정 접근 차단 — 예상대로)** |
| AI Search gov | 7,019 docs, 22 fields |

## 보관 정책

`backups/` 는 `.gitignore` 처리됨 — 절대 git 커밋 금지 (PII·키 포함). 신규 구독 cutover 완료 후 1개월간 외부 cold storage 보관, 이후 폐기.

## 주기 재실행

cutover D-day 직전(T-0)에 본 런북의 ②~④, ⑥을 **다시 한 번** 실행한다 — `--since <ISO>` 옵션으로 사전 백업 이후 증분만 export. 실제 cutover는 별도 런북 (`docs/runbooks/azure-cutover.md`, 본 PR 범위 외).
