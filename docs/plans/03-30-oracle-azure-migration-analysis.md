# Oracle DB → Azure 마이그레이션 가능성 분석

## 현황 요약

### 문제의 핵심

현재 **TERRY(인터랙티브 지도)**와 **CHOI(locationAgent_DB)**가 팀원 로컬 서버의 Oracle DB에 직접 연결되어 있습니다.

```
TERRY 백엔드 (로컬 8681/8682포트)
    ↓  TCP 1521 (하드코딩: "shobi/8680@//10.1.92.119:1521/xe")
Oracle XE @ 10.1.92.119 ← 팀원 로컬 서버

CHOI locationAgent_DB (로컬 8000포트)
    ↓  TCP 1521 (env: ORACLE_USER/ORACLE_PASSWORD/ORACLE_DSN)
Oracle XE @ 동일 서버
```

이 구조는 **단일 장애점(SPOF)** — 팀원 PC가 꺼지거나 네트워크가 바뀌면 두 기능 모두 중단됩니다.

### 현재 Oracle DB 사용 현황 (코드 분석 결과)

| 컴포넌트 | 접속 방식 | 사용 테이블 | 데이터 범위 |
|---------|----------|-----------|-----------|
| TERRY 인터랙티브 지도 | 하드코딩 IP | `SANGKWON_SALES`, `SANGKWON_STORE`, `STORE_SEOUL` 외 15개, `V_SANGKWON_LATEST` VIEW | 2019Q1~2025Q3, 208 행정동, 16개 지역 점포 GPS |
| CHOI locationAgent_DB | `.env` 환경변수 | `SANGKWON_SALES`, `SANGKWON_STORE` | 동일 |
| CHOI locationAgent_sang | **로컬 SQLite** (54MB) | `commercial_sales` (87,179행), `commercial_store` (306,889행) | 2024 Q1-Q4, 1,581개 상권 |
| integrated_PARK | **로컬 SQLite** (13MB) | `commercial_sales`, `commercial_store` | 2024 Q4, 서울 |

**Oracle DB 크기 근거:** `SANGKWON_SALES` 7M+행 × 40개 컬럼 + `STORE_*` 16개 테이블(GPS 포함) + 분기 누적 → ~5GB 타당

**핵심 구분:** 5GB Oracle DB는 TERRY + CHOI(locationAgent_DB)만 사용. `integrated_PARK`와 `locationAgent_sang`는 이미 독립적인 SQLite 사용 중.

---

## Azure 이전 가능 여부: **가능**

5GB는 Azure 데이터베이스 서비스에서 매우 소규모입니다. 기술적 장애물은 없습니다.

---

## 이전 옵션 분석

### Option A: Azure Database for PostgreSQL Flexible Server ★ 권장

| 항목 | 내용 |
|-----|------|
| 비용 | ~₩55,000–₩110,000/월 (Burstable B2ms, 32GB storage) |
| 마이그레이션 노력 | **중간** — Oracle SQL → PostgreSQL 문법 변환 필요 |
| 성능 | Oracle과 동급 이상 (인덱스 쿼리 기준) |
| Azure 통합 | Managed Identity 인증 지원, VNet peering |
| 특이사항 | `oracledb` → `asyncpg` 드라이버 교체 필요 |

**코드 변경 범위:**
- `TERRY/p01_backEnd/DAO/baseDAO.py` — 커넥션 풀 교체
- `CHOI/locationAgent_DB/db/repository.py` — 쿼리 문법 검토 (대부분 표준 SQL)
- `integrated_PARK/.env` — DB 접속 정보 교체

**Oracle 특수 문법 리스크:** 현재 쿼리는 `SELECT ... FROM ... WHERE` 표준 SQL 위주로, `ROWNUM`, `CONNECT BY` 등 Oracle 전용 문법 사용 여부 확인 필요.

---

### Option B: Oracle XE on Azure VM

| 항목 | 내용 |
|-----|------|
| 비용 | ~₩80,000–₩200,000/월 (Standard_B2s VM + 64GB 디스크) |
| 마이그레이션 노력 | **최소** — 코드 무변경, IP만 교체 |
| 성능 | 현재와 동일 |
| Azure 통합 | 수동 네트워크 설정 필요 |
| 특이사항 | VM 관리·패치 책임이 팀에게 있음, Oracle XE 제약(2 CPU, 2GB SGA) |

---

### Option C: Azure SQL Database (SQL Server)

| 항목 | 내용 |
|-----|------|
| 비용 | ~₩45,000–₩90,000/월 (General Purpose Serverless, 5GB) |
| 마이그레이션 노력 | **중간** — T-SQL 문법 변환 필요 |
| 성능 | 우수, 자동 스케일링 |
| 특이사항 | SQL Server 생태계, SSMA(마이그레이션 도구) 공식 지원 |

---

### Option D: 정적 데이터 → Azure Blob + DuckDB (분석 전용)

| 항목 | 내용 |
|-----|------|
| 비용 | ~₩3,000–₩10,000/월 (Blob Storage만) |
| 마이그레이션 노력 | **낮음** — 데이터 Parquet 변환 후 업로드 |
| 성능 | 분석 쿼리 매우 빠름 (인메모리), 단순 구조 적합 |
| 제약 | SANGKWON_* 같은 분기별 집계 데이터에만 적합, STORE_* 실시간 조회에는 부적합 |

---

## 성능 비교 (예상)

| 측정 항목 | 현재 (로컬 Oracle) | Azure PostgreSQL | Oracle on VM |
|---------|----------------|-----------------|-------------|
| 쿼리 응답 (Container Apps → DB) | ~50–200ms (인터넷 경유) | **~5–20ms** (VNet 내부) | ~10–30ms (VNet 내부) |
| 연결 안정성 | 불안정 (PC 종속) | **99.99% SLA** | 99.9% SLA |
| 동시 연결 | Oracle XE 한계 | **무제한** (tier 내) | Oracle XE 한계 동일 |
| pandas 캐시 효과 | 필수 (느린 연결 보완) | 보조적 (빠른 원본 조회 가능) | 보조적 |
| 데이터 업데이트 | 수동 (팀원 작업) | CI/CD 자동화 가능 | 수동 |

현재 Azure Container Apps에서 로컬 Oracle로의 쿼리는 **공인 인터넷을 경유**하므로 레이턴시가 높습니다. Azure 내부 VNet으로 이전하면 **10배 이상 응답 개선**이 가능합니다.

---

## 구조적 편의성 개선

### 현재의 구조적 문제

```
[문제 1] 단일 장애점
팀원 PC 종료 → Oracle 접속 불가 → production 전체 장애

[문제 2] 팀원별 로컬 환경 의존
TERRY, CHOI 각자 로컬 Oracle에 연결 → "내 PC에서만 됨" 현상

[문제 3] 보안 위험
Oracle 접속 정보(10.1.92.119:1521, shobi/8680)가 코드에 하드코딩
공인 인터넷에서 Oracle 포트 오픈 여부 확인 필요

[문제 4] 데이터 일관성 없음
팀원마다 Oracle DB 버전·데이터가 다를 수 있음
```

### Azure 이전 후 개선

```
[개선 1] 단일 진실의 원천 (Single Source of Truth)
모든 팀원이 동일한 Azure DB에 연결 → 데이터 일관성 보장

[개선 2] 환경 독립성
로컬 PC에 Oracle 설치 불필요
.env 파일의 CONNECTION_STRING만 변경하면 즉시 개발 가능

[개선 3] Managed Identity 인증
패스워드 없는 인증 → .env에서 Oracle 패스워드 제거 가능
(Azure PostgreSQL + Managed Identity 조합 시)

[개선 4] 자동 백업
Azure DB 서비스는 7–35일 Point-in-Time Restore 기본 제공

[개선 5] 스케일링
수요 증가 시 UI에서 CPU/메모리 슬라이더만 조정
```

---

## 권장 마이그레이션 경로

### 단계 1: 데이터 내보내기 (1일)
```bash
# Oracle에서 CSV 덤프
expdp shobi/8680@10.1.92.119:1521/xe \
  TABLES=SANGKWON_SALES,SANGKWON_STORE,STORE_SEOUL,...
```

### 단계 2: Azure PostgreSQL Flexible Server 생성 (30분)
```bash
az postgres flexible-server create \
  --name sohobi-db \
  --resource-group sohobi-rg \
  --location koreacentral \
  --sku-name Standard_B2ms \
  --storage-size 64
```

### 단계 3: 스키마 변환 및 데이터 로드 (1–2일)
- Oracle DDL → PostgreSQL DDL 변환 (주로 타입명 차이: `VARCHAR2` → `VARCHAR`, `NUMBER` → `NUMERIC`)
- `pg_restore` 또는 `COPY` 명령으로 데이터 삽입

### 단계 4: 코드 수정 (1일)
- `oracledb` → `asyncpg` 또는 `psycopg2` 교체
- `baseDAO.py`, `repository.py` 드라이버 코드 수정
- 환경변수 업데이트

### 단계 5: 검증 (1일)
- 기존 API 엔드포인트 동일 응답 확인
- 쿼리 성능 벤치마크

**총 예상 소요:** 4–5일 (DB 규모 5GB 기준)

---

## 결론

| 질문 | 답변 |
|-----|-----|
| Azure 이전 가능한가? | **예** — 5GB는 소규모, 기술적 장애 없음 |
| 가장 좋은 옵션은? | **Azure PostgreSQL Flexible Server** (비용·성능·통합 균형) |
| 코드 변경 최소화 원한다면? | **Oracle on Azure VM** (IP 교체만, 단 비용·관리 부담) |
| 성능 개선은 얼마나? | DB 쿼리 레이턴시 **10배 이상 단축** (인터넷 → VNet 내부) |
| 구조 편의성은? | 단일 장애점 제거, 팀원 로컬 환경 독립, 자동 백업 확보 |

현재 구조(production이 팀원 로컬 Oracle에 의존)는 **즉시 해결해야 할 아키텍처 리스크**입니다.
