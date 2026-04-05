# Oracle → Azure PostgreSQL Flexible Server 이전 계획

## Context

현재 `integrated_PARK`의 상권 에이전트(LocationAgent)는 Oracle DB에 연결하여
`SANGKWON_SALES` / `SANGKWON_STORE` 두 테이블을 조회한다.
Oracle 라이선스 비용 및 관리 부담을 줄이고, 이미 사용 중인 Azure 생태계로 DB를 통합하기 위해
Azure PostgreSQL Flexible Server로 이전한다.

---

## 현재 DB 현황

| 항목 | 내용 |
|------|------|
| 엔진 | Oracle (oracledb 2.5.0) |
| 테이블 | `SANGKWON_SALES` (매출), `SANGKWON_STORE` (점포수/개폐업률) |
| 접속 방식 | Connection Pool (min=2, max=5) |
| 파라미터 바인딩 | Oracle 스타일 `:1`, `:2`, … `:N` |
| 환경변수 | `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_HOST`, `ORACLE_PORT`, `ORACLE_SID` |
| 연결 파일 | `integrated_PARK/db/repository.py` |
| 배포 환경 | Azure Container Apps (Docker) |

### SANGKWON_SALES 주요 컬럼
`BASE_YR_QTR_CD`, `ADM_CD`, `ADM_NM`, `SVC_INDUTY_CD`, `SVC_INDUTY_NM`,
`TOT_SALES_AMT`, `TOT_SELNG_CO`, `MDWK_SALES_AMT`, `WKEND_SALES_AMT`,
`MON~SUN_SALES_AMT`, `TM00_06~TM21_24_SALES_AMT`, `ML/FML_SALES_AMT`,
`AGE10~AGE60_AMT`

### SANGKWON_STORE 주요 컬럼
`BASE_YR_QTR_CD`, `ADM_CD`, `ADM_NM`, `SVC_INDUTY_CD`, `SVC_INDUTY_NM`,
`STOR_CO`, `SIMILR_INDUTY_STOR_CO`, `OPBIZ_RT`, `OPBIZ_STOR_CO`,
`CLSBIZ_RT`, `CLSBIZ_STOR_CO`, `FRC_STOR_CO`

---

## 단계별 이전 계획

### Step 1 — Azure PostgreSQL Flexible Server 프로비저닝

Azure Portal 또는 Azure CLI로 생성:

```bash
az postgres flexible-server create \
  --resource-group <rg> \
  --name sohobi-pg \
  --location koreacentral \
  --admin-user <pguser> \
  --admin-password <pgpassword> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16
```

- SKU: `Standard_B1ms` (Burstable) — 소규모 read-heavy 워크로드에 적합
- 방화벽: Container Apps 아웃바운드 IP 허용 (또는 VNet 통합)
- SSL 강제: `require_secure_transport=ON` 유지

---

### Step 2 — PostgreSQL 스키마 생성

`integrated_PARK/db/schema_pg.sql` 파일을 PostgreSQL에 실행:

```bash
psql "host=sohobi-pg.postgres.database.azure.com dbname=sohobi user=<user> sslmode=require" \
  -f integrated_PARK/db/schema_pg.sql
```

---

### Step 3 — 데이터 마이그레이션

Oracle → PostgreSQL 데이터 이전. 두 가지 방법:

**방법 A (권장): Oracle → CSV → PostgreSQL**
```bash
# 1. Oracle에서 CSV 덤프
.venv/bin/python3 integrated_PARK/db/export_oracle_to_csv.py

# 2. PostgreSQL에 COPY로 적재
psql $PG_DSN -c "\COPY sangkwon_sales FROM 'sangkwon_sales.csv' CSV HEADER"
psql $PG_DSN -c "\COPY sangkwon_store FROM 'sangkwon_store.csv' CSV HEADER"
```

**방법 B: pgloader (직접 전환)**
```bash
pgloader oracle://user:pass@host/sid \
         postgresql://user:pass@pghost/sohobi \
         --with "quote identifiers"
```

---

### Step 4 — `repository.py` 코드 수정

**파일:** `integrated_PARK/db/repository.py`

| 항목 | Before (Oracle) | After (PostgreSQL) |
|------|----------------|-------------------|
| import | `import oracledb` | `import psycopg2; from psycopg2 import pool` |
| 풀 생성 | `oracledb.create_pool(user, password, host, port, sid, min=2, max=5)` | `pool.ThreadedConnectionPool(2, 5, host, port, dbname, user, password, sslmode="require")` |
| 커넥션 획득 | `cls._pool.acquire()` | `cls._pool.getconn()` |
| 커넥션 반납 | 자동 (context manager) | `cls._pool.putconn(conn)` |
| 파라미터 바인딩 | `:1`, `:2`, `:N` | `%s` (모두 동일) |
| IN 절 | `IN (:1, :2, ...)` | `IN (%s, %s, ...)` |
| 테이블명 | `SANGKWON_SALES` | `sangkwon_sales` |
| 환경변수 | `ORACLE_*` | `PG_*` |

---

### Step 5 — requirements.txt 업데이트

```diff
- oracledb==2.5.0
+ psycopg2-binary==2.9.9
```

---

### Step 6 — 환경변수 교체

**.env (로컬)**
```ini
# 제거
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_HOST=...
ORACLE_PORT=...
ORACLE_SID=...

# 추가
PG_HOST=sohobi-pg.postgres.database.azure.com
PG_PORT=5432
PG_DB=sohobi
PG_USER=<pguser>
PG_PASSWORD=<pgpassword>
```

**Azure Container Apps 시크릿** (Portal 또는 CLI):
```bash
az containerapp secret set --name sohobi-api --resource-group <rg> \
  --secrets pg-host="sohobi-pg.postgres.database.azure.com" \
             pg-db="sohobi" \
             pg-user="<pguser>" \
             pg-password="<pgpassword>"
```

---

### Step 7 — Dockerfile 확인

`psycopg2-binary`는 libpq 내장이므로 Dockerfile에 추가 apt 패키지 불필요.
`python:3.12-slim-bookworm` 기반 이미지에서 그대로 빌드 가능.

---

### Step 8 — 로컬 검증

```bash
cd integrated_PARK
source .env
.venv/bin/python3 -c "
from db.repository import CommercialRepository
repo = CommercialRepository()
print(repo.get_supported_locations()[:5])
result = repo.get_sales('홍대', '한식')
print(result['summary'])
"
```

---

### Step 9 — 배포 및 최종 검증

```bash
# Docker 빌드 후 Container Apps 배포
az containerapp update --name sohobi-api --resource-group <rg> \
  --image <registry>/sohobi-api:latest

# API 엔드포인트 smoke test
curl -X POST $BACKEND_HOST/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대 한식 창업 분석해줘"}'
```

---

## 수정 대상 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/db/repository.py` | oracledb → psycopg2, SQL 파라미터 바인딩(`%s`), 테이블명 소문자, 커넥션 풀 교체 |
| `integrated_PARK/db/finance_db.py` | oracledb → psycopg2, named params(`:x` → `%(x)s`), 테이블명 소문자, PG_* 환경변수 |
| `integrated_PARK/requirements.txt` | oracledb 제거, psycopg2-binary 추가 |
| `integrated_PARK/.env` | ORACLE_* 제거, PG_* 추가 (수동) |
| `integrated_PARK/db/schema_pg.sql` | 신규: PostgreSQL DDL |
| `integrated_PARK/db/export_oracle_to_csv.py` | 신규: 데이터 내보내기 스크립트 |

> **주의**: `finance_db.py`는 초기 계획에서 누락된 파일. Oracle `SANGKWON_SALES` 동일 테이블 사용,
> named parameter 방식(`:region`) → psycopg2에서 `%(region)s` 변환 필요.

## 검증 포인트

- [ ] `sangkwon_sales` 행 수 Oracle 원본과 일치
- [ ] `sangkwon_store` 행 수 Oracle 원본과 일치
- [ ] `get_sales("홍대", "한식")` 반환값 Oracle 결과와 동일
- [ ] `get_store_count("강남", "카페")` 반환값 동일
- [ ] `get_similar_locations("치킨")` top 3 결과 동일
- [ ] API `/api/v1/query` 상권 관련 질문에 정상 응답
