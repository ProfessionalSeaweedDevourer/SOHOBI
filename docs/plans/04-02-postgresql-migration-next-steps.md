# PostgreSQL 이전 실행 가이드

**작성일:** 2026-04-02
**목적:** 코드 변경 완료 후 인프라·데이터·배포 단계 실행 가이드

코드 변경(`repository.py`, `finance_db.py`, `requirements.txt`, `schema_pg.sql`)은 완료된 상태이다.
이 문서는 Azure PostgreSQL Flexible Server를 실제로 프로비저닝하고 데이터를 이전하여 배포하기까지
수동으로 실행해야 하는 절차를 단계별로 설명한다.

---

## 사전 준비 체크리스트

실행 전 아래 조건을 확인한다.

- [ ] `az account show` — Azure CLI 로그인 확인
- [ ] 대상 리소스 그룹명 파악
- [ ] 팀원 PC 전원 ON + Tailscale 실행 중 (Oracle 데이터 내보내기 시 필요)

---

## Step 1 — SSH 터널 열기 (Oracle 데이터 내보내기 전용)

Oracle DB(`<ORACLE_HOST>:1521`)는 유선 LAN에만 존재하므로 Tailscale을 통해 SSH 터널로 접근한다.
**데이터 내보내기(Step 5)가 끝나면 터널을 닫아도 된다.**

```bash
# 터미널 하나를 전용으로 유지 (Ctrl+C로 종료)
ssh -N -L 1521:<ORACLE_HOST>:1521 soldesk@<팀원_tailscale_IP>
# 비밀번호: 1234
```

터널 확인:

```bash
nc -z -w 3 localhost 1521 && echo "터널 OK"
```

---

## Step 2 — Azure PostgreSQL Flexible Server 프로비저닝

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

**방화벽 설정** — Container Apps 아웃바운드 IP를 허용한다.

```bash
# Container Apps 아웃바운드 IP 확인
az containerapp show --name sohobi-api --resource-group <rg> \
  --query "properties.outboundIpAddresses" -o tsv

# 허용 규칙 추가 (IP마다 반복)
az postgres flexible-server firewall-rule create \
  --resource-group <rg> --name sohobi-pg \
  --rule-name allow-containerapp \
  --start-ip-address <ip> --end-ip-address <ip>
```

SSL 강제(`require_secure_transport=ON`)는 기본 활성화되어 있으므로 별도 설정 불필요하다.

---

## Step 3 — DB 생성 및 스키마 적용

```bash
# DB 생성
az postgres flexible-server db create \
  --resource-group <rg> \
  --server-name sohobi-pg \
  --database-name sohobi

# 스키마 적용 (sangkwon_sales, sangkwon_store 테이블 + 인덱스)
psql "host=sohobi-pg.postgres.database.azure.com \
      dbname=sohobi user=<pguser> sslmode=require" \
  -f integrated_PARK/db/schema_pg.sql
```

적용 확인:

```bash
psql "host=sohobi-pg.postgres.database.azure.com \
      dbname=sohobi user=<pguser> sslmode=require" \
  -c "\dt"
# sangkwon_sales, sangkwon_store 두 테이블이 보여야 함
```

---

## Step 4 — Oracle에서 CSV 내보내기

SSH 터널(Step 1)이 열려 있는 상태에서 실행한다.

```bash
cd integrated_PARK
source .env   # ORACLE_* 변수 로드 (ORACLE_HOST=localhost)
.venv/bin/python3 db/export_oracle_to_csv.py
```

정상 출력 예시:

```
[SANGKWON_SALES] 조회 중...
[SANGKWON_SALES] 21664행 → .../db/sangkwon_sales.csv
[SANGKWON_STORE] 조회 중...
[SANGKWON_STORE] 76445행 → .../db/sangkwon_store.csv
```

행 수 검증 (헤더 행 제외하고 원본과 일치해야 함):

```bash
# 헤더 포함이므로 실제 데이터 행 수 = wc -l 결과 - 1
wc -l integrated_PARK/db/sangkwon_sales.csv
wc -l integrated_PARK/db/sangkwon_store.csv
```

> **주의:** CSV 파일은 `.gitignore`에 추가하거나 내보내기 후 즉시 삭제한다.
> 민감 데이터는 저장소에 커밋하지 않는다.

---

## Step 5 — PostgreSQL에 데이터 적재

```bash
export PG_DSN="host=sohobi-pg.postgres.database.azure.com \
               dbname=sohobi user=<pguser> sslmode=require"

# sangkwon_sales 적재
psql "$PG_DSN" -c "\COPY sangkwon_sales(
  base_yr_qtr_cd, adm_cd, adm_nm, svc_induty_cd, svc_induty_nm,
  tot_sales_amt, tot_selng_co, mdwk_sales_amt, wkend_sales_amt,
  mon_sales_amt, tue_sales_amt, wed_sales_amt, thu_sales_amt,
  fri_sales_amt, sat_sales_amt, sun_sales_amt,
  tm00_06_sales_amt, tm06_11_sales_amt, tm11_14_sales_amt,
  tm14_17_sales_amt, tm17_21_sales_amt, tm21_24_sales_amt,
  ml_sales_amt, fml_sales_amt,
  age10_amt, age20_amt, age30_amt, age40_amt, age50_amt, age60_amt
) FROM 'integrated_PARK/db/sangkwon_sales.csv' CSV HEADER"

# sangkwon_store 적재
psql "$PG_DSN" -c "\COPY sangkwon_store(
  base_yr_qtr_cd, adm_cd, adm_nm, svc_induty_cd, svc_induty_nm,
  stor_co, similr_induty_stor_co,
  opbiz_rt, opbiz_stor_co,
  clsbiz_rt, clsbiz_stor_co,
  frc_stor_co
) FROM 'integrated_PARK/db/sangkwon_store.csv' CSV HEADER"
```

행 수 재확인:

```bash
psql "$PG_DSN" -c "SELECT COUNT(*) FROM sangkwon_sales;"
psql "$PG_DSN" -c "SELECT COUNT(*) FROM sangkwon_store;"
# Oracle 원본 수와 일치해야 함
```

---

## Step 6 — 로컬 `.env` 환경변수 교체

`.env`에서 Oracle 변수를 제거하고 PostgreSQL 변수를 추가한다.

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
PG_SSLMODE=require
```

> **주의:** `.env`는 절대 커밋하지 않는다.

---

## Step 7 — 로컬 검증

```bash
cd integrated_PARK

# 의존성 재설치 (oracledb 제거, psycopg2-binary 설치)
.venv/bin/pip install -r requirements.txt

source .env

# repository.py 검증
.venv/bin/python3 -c "
from db.repository import CommercialRepository
repo = CommercialRepository()
r = repo.get_sales('홍대', '한식')
print('get_sales:', r['summary']['monthly_sales_krw'])
r2 = repo.get_store_count('강남', '카페')
print('get_store_count:', r2['summary']['store_count'])
r3 = repo.get_similar_locations('치킨', top_n=3)
print('similar_locations:', [x['adm_name'] for x in r3])
"

# finance_db.py 검증
.venv/bin/python3 -c "
from db.finance_db import DBWork
db = DBWork()
avg = db.get_average_sales()
print('avg_sales:', avg)
# [17000000] 이 나오면 fallback — DB 연결 실패
"
```

두 결과 모두 fallback 값(`[17000000]`)이 아닌 실제 DB 값이 나와야 한다.

---

## Step 8 — Azure Container Apps 시크릿 업데이트

```bash
# PostgreSQL 시크릿 등록
az containerapp secret set \
  --name sohobi-api \
  --resource-group <rg> \
  --secrets \
    pg-host="sohobi-pg.postgres.database.azure.com" \
    pg-db="sohobi" \
    pg-user="<pguser>" \
    pg-password="<pgpassword>"

# 환경변수에 시크릿 참조 연결
az containerapp update \
  --name sohobi-api \
  --resource-group <rg> \
  --set-env-vars \
    PG_HOST=secretref:pg-host \
    PG_DB=secretref:pg-db \
    PG_USER=secretref:pg-user \
    PG_PASSWORD=secretref:pg-password \
    PG_PORT=5432 \
    PG_SSLMODE=require
```

---

## Step 9 — Docker 이미지 빌드 및 배포

```bash
# ACR 사용 시 (권장)
az acr build \
  --registry <acr-name> \
  --image sohobi-api:latest \
  integrated_PARK/

# Container Apps 이미지 업데이트
az containerapp update \
  --name sohobi-api \
  --resource-group <rg> \
  --image <acr-name>.azurecr.io/sohobi-api:latest
```

배포 상태 확인:

```bash
az containerapp revision list \
  --name sohobi-api \
  --resource-group <rg> \
  --query "[].{name:name, active:properties.active, replicas:properties.replicas}" \
  -o table
```

---

## Step 10 — 배포 후 API 검증

```bash
source integrated_PARK/.env  # BACKEND_HOST 로드

# 상권 분석 질문
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대 한식 창업 분석해줘"}' | python3 -m json.tool

# 재무 시뮬레이션 질문 (finance_db.py 검증)
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "강남 카페 창업 시 초기비용 3000만원으로 수익 시뮬레이션 해줘"}' \
  | python3 -m json.tool
```

응답의 `status`가 `"approved"`, `grade`가 `"A"` 또는 `"B"`이면 정상이다.

---

## Step 11 — Oracle 연결 정리 (검증 완료 후)

검증이 완료된 뒤 Oracle 관련 항목을 정리한다.

```bash
# Container Apps에서 Oracle 시크릿 삭제 (있다면)
az containerapp secret remove \
  --name sohobi-api \
  --resource-group <rg> \
  --secret-names oracle-user oracle-password oracle-host oracle-sid

# SSH 터널 종료 (Step 1 터미널에서 Ctrl+C)
```

로컬 `.env`에서도 `ORACLE_*` 변수를 삭제한다.

---

## 검증 체크리스트

| 항목 | 확인 방법 | 기대 결과 |
|------|----------|----------|
| DB 행 수 일치 | `SELECT COUNT(*)` vs `wc -l` | Oracle 원본과 동일 |
| `get_sales("홍대", "한식")` | 로컬 Python 실행 | `monthly_sales_krw` > 0 |
| `get_store_count("강남", "카페")` | 로컬 Python 실행 | `store_count` > 0 |
| `get_average_sales()` | 로컬 Python 실행 | 실제 평균값 (17000000 아님) |
| API 상권 질문 | curl | `status: approved` |
| API 재무 질문 | curl | `status: approved` |
