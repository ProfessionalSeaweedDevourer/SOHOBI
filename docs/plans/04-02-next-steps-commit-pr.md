# 작업 계획: 다음 단계 문서 작성 + 커밋 + PR

## 목표

1. 마이그레이션 실행 가이드 문서(`docs/plans/2026-04-02-postgresql-migration-next-steps.md`) 신규 작성
2. 이번 세션 변경 파일 전체를 하나의 커밋으로 묶기
3. PARK → main PR 오픈

---

## Step 1 — 신규 문서 작성

**파일:** `docs/plans/2026-04-02-postgresql-migration-next-steps.md`

아래 순서로 섹션을 구성한다:

### 1. 개요
- 이전 배경: Oracle 로컬 LAN → Azure PostgreSQL Flexible Server
- 코드 변경은 완료됨; 이 문서는 **인프라·데이터·배포** 실행 가이드

### 2. 사전 확인 체크리스트
- Azure CLI 로그인 (`az account show`)
- 대상 리소스 그룹 확인
- Oracle SSH 터널 열기 (데이터 내보내기 시 필요)
  ```bash
  ssh -N -L 1521:<ORACLE_HOST>:1521 soldesk@<tailscale-ip>
  ```

### 3. Azure PostgreSQL Flexible Server 프로비저닝
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
- 방화벽: Container Apps 아웃바운드 IP 허용
- SSL 강제(`require_secure_transport=ON`) 유지

### 4. DB·스키마 생성
```bash
# DB 생성
az postgres flexible-server db create \
  --resource-group <rg> --server-name sohobi-pg --database-name sohobi

# 스키마 적용
psql "host=sohobi-pg.postgres.database.azure.com dbname=sohobi \
      user=<pguser> sslmode=require" \
  -f integrated_PARK/db/schema_pg.sql
```

### 5. 데이터 내보내기 (Oracle → CSV)
```bash
cd integrated_PARK
source .env   # ORACLE_* 변수 로드, ORACLE_HOST=localhost (SSH 터널)
.venv/bin/python3 db/export_oracle_to_csv.py
# 출력: db/sangkwon_sales.csv, db/sangkwon_store.csv
```
행 수 검증:
```bash
wc -l db/sangkwon_sales.csv   # 헤더 포함 → 기대값 + 1
wc -l db/sangkwon_store.csv
```

### 6. 데이터 적재 (CSV → PostgreSQL)
```bash
export PG_DSN="host=sohobi-pg.postgres.database.azure.com dbname=sohobi user=<pguser> sslmode=require"

psql "$PG_DSN" -c "\COPY sangkwon_sales(base_yr_qtr_cd,adm_cd,adm_nm,svc_induty_cd,svc_induty_nm,tot_sales_amt,tot_selng_co,mdwk_sales_amt,wkend_sales_amt,mon_sales_amt,tue_sales_amt,wed_sales_amt,thu_sales_amt,fri_sales_amt,sat_sales_amt,sun_sales_amt,tm00_06_sales_amt,tm06_11_sales_amt,tm11_14_sales_amt,tm14_17_sales_amt,tm17_21_sales_amt,tm21_24_sales_amt,ml_sales_amt,fml_sales_amt,age10_amt,age20_amt,age30_amt,age40_amt,age50_amt,age60_amt) FROM 'db/sangkwon_sales.csv' CSV HEADER"

psql "$PG_DSN" -c "\COPY sangkwon_store(base_yr_qtr_cd,adm_cd,adm_nm,svc_induty_cd,svc_induty_nm,stor_co,similr_induty_stor_co,opbiz_rt,opbiz_stor_co,clsbiz_rt,clsbiz_stor_co,frc_stor_co) FROM 'db/sangkwon_store.csv' CSV HEADER"
```
행 수 재확인:
```bash
psql "$PG_DSN" -c "SELECT COUNT(*) FROM sangkwon_sales;"
psql "$PG_DSN" -c "SELECT COUNT(*) FROM sangkwon_store;"
```

### 7. 로컬 환경변수 교체 (`.env`)
```ini
# 삭제
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
PG_SSLMODE=require
```

### 8. 로컬 검증
```bash
cd integrated_PARK
.venv/bin/pip install -r requirements.txt   # psycopg2-binary 설치

source .env
.venv/bin/python3 -c "
from db.repository import CommercialRepository
repo = CommercialRepository()
result = repo.get_sales('홍대', '한식')
print(result['summary'])
result2 = repo.get_store_count('강남', '카페')
print(result2['summary'])
"

.venv/bin/python3 -c "
from db.finance_db import DBWork
db = DBWork()
print(db.get_average_sales())
"
```

### 9. Azure Container Apps 시크릿 업데이트
```bash
az containerapp secret set --name sohobi-api --resource-group <rg> \
  --secrets \
    pg-host="sohobi-pg.postgres.database.azure.com" \
    pg-db="sohobi" \
    pg-user="<pguser>" \
    pg-password="<pgpassword>"

# 환경변수 참조 연결
az containerapp update --name sohobi-api --resource-group <rg> \
  --set-env-vars \
    PG_HOST=secretref:pg-host \
    PG_DB=secretref:pg-db \
    PG_USER=secretref:pg-user \
    PG_PASSWORD=secretref:pg-password \
    PG_PORT=5432 \
    PG_SSLMODE=require
```

### 10. Docker 빌드 및 배포
```bash
# 이미지 빌드
docker build -t sohobi-api:latest integrated_PARK/

# Container Registry push (ACR 사용 시)
az acr build --registry <acr-name> --image sohobi-api:latest integrated_PARK/

# Container Apps 업데이트
az containerapp update --name sohobi-api --resource-group <rg> \
  --image <acr-name>.azurecr.io/sohobi-api:latest
```

### 11. 배포 후 검증
```bash
source integrated_PARK/.env  # BACKEND_HOST 포함

curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대 한식 창업 분석해줘"}' | python3 -m json.tool

curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "강남 카페 평균 매출 알려줘"}' | python3 -m json.tool
```

### 12. 검증 완료 후 Oracle 연결 제거
- `.env`에서 `ORACLE_*` 변수 삭제
- Container Apps 시크릿에서 Oracle 관련 항목 삭제
- SSH 터널 종료

---

## Step 2 — 커밋

스테이징 파일:
- `integrated_PARK/db/repository.py`
- `integrated_PARK/db/finance_db.py`
- `integrated_PARK/requirements.txt`
- `integrated_PARK/db/schema_pg.sql` (신규)
- `integrated_PARK/db/export_oracle_to_csv.py` (신규)
- `docs/plans/2026-04-01-oracle-to-postgresql-migration.md` (신규)
- `docs/plans/2026-04-02-postgresql-migration-next-steps.md` (신규)

커밋 메시지:
```
feat: Oracle → Azure PostgreSQL Flexible Server 이전 코드 변경
```

---

## Step 3 — PR

- Base: `main` ← Head: `PARK`
- 제목: `feat: Oracle → Azure PostgreSQL Flexible Server 이전`
- 본문: 변경 파일 목록 + 남은 수동 단계 요약

---

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

Oracle DDL을 PostgreSQL DDL로 변환. 테이블명은 lowercase 권장.

**파일 위치:** `integrated_PARK/db/schema_pg.sql` (신규 생성)

```sql
-- sangkwon_sales
CREATE TABLE sangkwon_sales (
    id               BIGSERIAL PRIMARY KEY,
    base_yr_qtr_cd   VARCHAR(6)  NOT NULL,
    adm_cd           VARCHAR(10) NOT NULL,
    adm_nm           VARCHAR(50),
    svc_induty_cd    VARCHAR(20) NOT NULL,
    svc_induty_nm    VARCHAR(50),
    tot_sales_amt    BIGINT,
    tot_selng_co     INTEGER,
    mdwk_sales_amt   BIGINT,
    wkend_sales_amt  BIGINT,
    mon_sales_amt    BIGINT,
    tue_sales_amt    BIGINT,
    wed_sales_amt    BIGINT,
    thu_sales_amt    BIGINT,
    fri_sales_amt    BIGINT,
    sat_sales_amt    BIGINT,
    sun_sales_amt    BIGINT,
    tm00_06_sales_amt BIGINT,
    tm06_11_sales_amt BIGINT,
    tm11_14_sales_amt BIGINT,
    tm14_17_sales_amt BIGINT,
    tm17_21_sales_amt BIGINT,
    tm21_24_sales_amt BIGINT,
    ml_sales_amt     BIGINT,
    fml_sales_amt    BIGINT,
    age10_amt        BIGINT,
    age20_amt        BIGINT,
    age30_amt        BIGINT,
    age40_amt        BIGINT,
    age50_amt        BIGINT,
    age60_amt        BIGINT
);

CREATE INDEX idx_sales_lookup
  ON sangkwon_sales (base_yr_qtr_cd, adm_cd, svc_induty_cd);

-- sangkwon_store
CREATE TABLE sangkwon_store (
    id                   BIGSERIAL PRIMARY KEY,
    base_yr_qtr_cd       VARCHAR(6)  NOT NULL,
    adm_cd               VARCHAR(10) NOT NULL,
    adm_nm               VARCHAR(50),
    svc_induty_cd        VARCHAR(20) NOT NULL,
    svc_induty_nm        VARCHAR(50),
    stor_co              INTEGER,
    similr_induty_stor_co INTEGER,
    opbiz_rt             NUMERIC(6,2),
    opbiz_stor_co        INTEGER,
    clsbiz_rt            NUMERIC(6,2),
    clsbiz_stor_co       INTEGER,
    frc_stor_co          INTEGER
);

CREATE INDEX idx_store_lookup
  ON sangkwon_store (base_yr_qtr_cd, adm_cd, svc_induty_cd);
```

---

### Step 3 — 데이터 마이그레이션

Oracle → PostgreSQL 데이터 이전. 두 가지 방법 중 선택:

**방법 A (권장): Oracle → CSV → PostgreSQL**
```bash
# 1. Oracle에서 CSV 덤프 (sqlplus 또는 Python oracledb)
python3 integrated_PARK/db/export_oracle_to_csv.py   # 신규 스크립트

# 2. PostgreSQL에 COPY로 적재
psql $PG_DSN -c "\COPY sangkwon_sales FROM 'sangkwon_sales.csv' CSV HEADER"
psql $PG_DSN -c "\COPY sangkwon_store FROM 'sangkwon_store.csv' CSV HEADER"
```

**방법 B: pgloader (자동 변환)**
```bash
pgloader oracle://user:pass@host/sid \
         postgresql://user:pass@pghost/sohobi \
         --with "quote identifiers"
```

---

### Step 4 — `repository.py` 코드 수정

**파일:** `integrated_PARK/db/repository.py`

변경 사항:
1. `import oracledb` → `import psycopg2`, `from psycopg2 import pool`
2. 커넥션 풀 교체:
   ```python
   # Before (Oracle)
   cls._pool = oracledb.create_pool(
       user=..., password=..., host=..., port=..., sid=..., min=2, max=5, increment=1
   )
   conn = cls._pool.acquire()

   # After (PostgreSQL)
   cls._pool = pool.ThreadedConnectionPool(
       minconn=2, maxconn=5,
       host=os.getenv("PG_HOST"),
       port=int(os.getenv("PG_PORT", "5432")),
       dbname=os.getenv("PG_DB"),
       user=os.getenv("PG_USER"),
       password=os.getenv("PG_PASSWORD"),
       sslmode="require",
   )
   conn = cls._pool.getconn()
   # 반납: cls._pool.putconn(conn)
   ```
3. 파라미터 바인딩 변환:
   ```python
   # Before (Oracle): ":1", ":2" → positional list
   cursor.execute(sql, [quarter] + adm_codes + [industry_code])

   # After (psycopg2): "%s" placeholders, same positional list
   cursor.execute(sql, [quarter] + adm_codes + [industry_code])
   # IN 절: f"IN ({','.join(['%s']*len(adm_codes))})"
   ```
4. 테이블명 소문자로 변경 (`SANGKWON_SALES` → `sangkwon_sales`)
5. 컬럼명은 psycopg2에서 이미 lowercase 반환 — `cursor.description` 처리 동일
6. 커넥션 컨텍스트 매니저:
   ```python
   conn = self._get_pool().getconn()
   try:
       with conn.cursor() as cursor:
           cursor.execute(sql, params)
           rows = cursor.fetchall()
   finally:
       self._get_pool().putconn(conn)
   ```

---

### Step 5 — requirements.txt 업데이트

```
# 제거
oracledb==2.5.0

# 추가
psycopg2-binary==2.9.9
```

---

### Step 6 — 환경변수 교체

**.env (로컬)**
```
# 제거: ORACLE_USER, ORACLE_PASSWORD, ORACLE_HOST, ORACLE_PORT, ORACLE_SID
# 추가:
PG_HOST=sohobi-pg.postgres.database.azure.com
PG_PORT=5432
PG_DB=sohobi
PG_USER=<pguser>@sohobi-pg
PG_PASSWORD=<pgpassword>
```

**Azure Container Apps 시크릿** (Portal 또는 CLI):
```bash
az containerapp secret set --name sohobi-api --resource-group <rg> \
  --secrets pg-host=sohobi-pg.postgres.database.azure.com \
             pg-db=sohobi \
             pg-user=<pguser> \
             pg-password=<pgpassword>
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
| `integrated_PARK/db/repository.py` | oracledb → psycopg2, SQL 파라미터 바인딩, 테이블명, 풀 교체 |
| `integrated_PARK/requirements.txt` | oracledb 제거, psycopg2-binary 추가 |
| `integrated_PARK/.env` | ORACLE_* 제거, PG_* 추가 |
| `integrated_PARK/db/schema_pg.sql` | 신규: PostgreSQL DDL |
| `integrated_PARK/db/export_oracle_to_csv.py` | 신규: 데이터 내보내기 스크립트 (Step 3) |

## 검증 포인트

- [ ] `sangkwon_sales` 행 수 Oracle 원본과 일치
- [ ] `sangkwon_store` 행 수 Oracle 원본과 일치
- [ ] `get_sales("홍대", "한식")` 반환값 Oracle 결과와 동일
- [ ] `get_store_count("강남", "카페")` 반환값 동일
- [ ] `get_similar_locations("치킨")` top 3 결과 동일
- [ ] API `/api/v1/query` 상권 관련 질문에 정상 응답
