# 로컬 Oracle DB → Azure 클라우드 마이그레이션 안

> 작성일: 2026-03-30
> 대상 독자: SOHOBI 개발팀 전원
> 목적: 현재 로컬 서버 DB 의존 구조의 문제점과 Azure 이전 방안 공유

---

## 핵심 요약

**지금 상황:** TERRY 지도, CHOI locationAgent 가 특정 PC에 있는 DB에 연결되어 돌아가고 있음.
**문제:** 그 PC가 꺼지면 두 기능 모두 멈춤.
**해결안:** DB를 Azure 클라우드로 옮기면 24/7 안정 운영 + 속도 향상 + 팀 협업 개선.
**작업 규모:** 약 1~2일.

---

## 1. 현재 구조와 문제점

### 지금 어떻게 연결되어 있나?

```
[TERRY 인터랙티브 지도 서버]
        |
        | (인터넷 경유, Oracle 포트 1521)
        ↓
[로컬 DB PC — Oracle DB, 약 5GB]
        ↑
        | (인터넷 경유)
        |
[CHOI locationAgent_DB 서버]
```

즉, **두 기능 모두 동일한 로컬 PC의 DB에 의존**하고 있음.

### 현재 발생하는 문제

| 문제 | 구체적 상황 |
|------|-----------|
| **서비스 중단 위험** | DB가 있는 PC를 끄거나 재시작하면 TERRY 지도와 CHOI locationAgent 동시 중단 |
| **속도 불안정** | Azure 서버 → 로컬 PC 간 일반 인터넷 경유 → 쿼리 응답 200ms~5초, 불규칙 |
| **IP 하드코딩** | TERRY 코드에 `10.1.92.119` IP가 직접 박혀 있어, 네트워크 변경 시 수동 수정 필요 |
| **팀원 환경 분리** | 각자 로컬에서 개발하면 DB 버전·데이터가 달라질 수 있음 |
| **백업 없음** | 로컬 PC 장애 시 5GB 데이터 손실 위험 |

---

## 2. 어떤 DB로 옮길 것인가?

이전 가능한 Azure 서비스를 비교합니다.

### 옵션 A: Azure Database for PostgreSQL Flexible Server ✅ 권장

> **한 줄 설명:** Oracle과 거의 비슷한 관계형 DB. AWS RDS에 해당하는 Azure 관리형 서비스.

| 항목 | 내용 |
|------|------|
| 월 비용 | 약 $30 (Burstable B2s 기준, 32GB SSD 포함) |
| 코드 변경 | Oracle SQL 문법 일부 수정 필요 (아래 상세 설명) |
| 지리공간 쿼리 | PostGIS 확장 지원 → GPS 반경 검색 대폭 향상 |
| Azure 통합 | Container Apps와 동일 VNet → 인터넷 경유 없이 내부 통신 |
| 백업 | 자동 백업 7~35일 보존, 분 단위 복구 |
| 운영 부담 | Azure가 패치·모니터링 담당, 팀은 신경 쓸 필요 없음 |

### 옵션 B: Azure VM에 Oracle XE 설치

> **한 줄 설명:** 지금 구조 그대로를 클라우드 VM으로 이사. 코드 변경 최소.

| 항목 | 내용 |
|------|------|
| 월 비용 | 약 $80~200 (VM + 디스크) |
| 코드 변경 | 거의 없음 (IP 주소만 교체) |
| 단점 | VM 직접 관리 필요, Oracle XE는 CPU 2개·메모리 2GB 제한 있음 |

### 옵션 C: Oracle Autonomous Database (Oracle Cloud 무료)

> **한 줄 설명:** Oracle이 제공하는 무료 클라우드 DB. SQL 재작성 없음.

| 항목 | 내용 |
|------|------|
| 월 비용 | **$0** (무료 티어, 인스턴스 2개·20GB 각) |
| 코드 변경 | 없음 — 기존 Oracle 코드 그대로 사용 |
| 단점 | Azure가 아닌 Oracle Cloud → 두 클라우드를 함께 관리해야 함, 네트워크 지연 증가 |

### 비교 요약

| | 권장 (PostgreSQL) | Oracle on VM | Oracle Cloud 무료 |
|--|:-:|:-:|:-:|
| 월 비용 | $30 | $80~200 | $0 |
| 코드 변경 | 중간 | 최소 | 없음 |
| Azure 통합 | 최상 | 좋음 | 보통 |
| 자동 백업 | ✅ | ❌ (수동) | ✅ |
| 무중단 SLA | 99.99% | 99.9% | 99.95% |
| 운영 편의성 | 최상 | 낮음 | 보통 |

---

## 3. 이전 후 달라지는 것

### 구조 변화

**이전:**
```
TERRY / CHOI 서버  →→→ (인터넷) →→→  로컬 PC Oracle DB
```

**이전 후:**
```
TERRY / CHOI 서버  →→  (Azure 내부 VNet, 0.1ms)  →→  Azure PostgreSQL
```

### 성능 개선 예상

| 쿼리 | 현재 | 이전 후 | 개선 |
|------|------|---------|------|
| 단일 행정동 매출 조회 | 200~500ms | 10~50ms | **5~10배** |
| 업종별 집계 쿼리 | 1~3초 | 50~200ms | **5~15배** |
| GPS 반경 점포 검색 | 2~5초 | 20~100ms | **20~50배** |
| 서버 시작 시 데이터 로드 | 10~30초 | 2~5초 | **5배** |
| 전체 응답 (LLM 포함) | 6~10초 | 3~5초 | **2배** |

> GPS 검색이 가장 크게 개선되는 이유: PostgreSQL의 **PostGIS** 공간 인덱스를 활용하면 수백만 개 좌표에서 반경 검색을 인덱스 스캔으로 처리 가능. 현재는 풀스캔 방식.

### 팀 협업 관점 개선

| 지금 | 이전 후 |
|------|---------|
| 특정 팀원 PC가 켜져 있어야 작동 | 24/7 독립 운영 |
| 팀원마다 로컬 Oracle 설치·관리 | `.env` 파일 하나만 바꾸면 즉시 연결 |
| 데이터가 PC마다 다를 수 있음 | 모든 팀원이 동일한 DB 사용 |
| 백업 없음 | 자동 백업 (7~35일 분 단위 복구) |
| 로그·모니터링 없음 | Azure Portal에서 쿼리 성능·CPU·연결 수 실시간 확인 |

---

## 4. 코드 변경 범위 (PostgreSQL 선택 시)

### 변경이 필요한 파일

| 파일 | 변경 내용 | 난이도 |
|------|-----------|--------|
| `TERRY/p01_backEnd/DAO/fable/oracleDBConnect.py` | `oracledb` → `asyncpg` 드라이버 교체 | 낮음 |
| `TERRY/p01_backEnd/DAO/sangkwonDAO.py` | SQL 문법 수정 | 중간 |
| `TERRY/p01_backEnd/DAO/sangkwonStoreDAO.py` | SQL 문법 수정 | 중간 |
| `TERRY/p01_backEnd/DAO/mapInfoDAO.py` | GPS 쿼리 → PostGIS 방식으로 개선 | 낮음 |
| `CHOI/locationAgent_DB/db/repository.py` | 드라이버 교체 + SQL 수정 | 중간 |
| `.env` 파일들 | `ORACLE_DSN` → `POSTGRES_URL` | 낮음 |

### SQL 문법 차이 (수정 예시)

```sql
-- Oracle (현재)
SELECT * FROM SANGKWON_SALES WHERE ADM_CD = :cd AND ROWNUM <= 10

-- PostgreSQL (이전 후)
SELECT * FROM sangkwon_sales WHERE adm_cd = $1 LIMIT 10
```

```python
# Oracle 바인드 파라미터
cursor.execute("SELECT ... WHERE adm_cd = :cd", {"cd": adm_cd})

# PostgreSQL 바인드 파라미터 (asyncpg)
await conn.fetch("SELECT ... WHERE adm_cd = $1", adm_cd)
```

주요 변환 목록:
- `:파라미터명` → `$1`, `$2` (asyncpg 기준)
- `ROWNUM` → `LIMIT`
- `NVL(값, 대체값)` → `COALESCE(값, 대체값)`
- `VARCHAR2` 타입 → `VARCHAR`
- `NUMBER` 타입 → `NUMERIC` 또는 `INTEGER`

### 변경이 필요 없는 것

- `integrated_PARK/` — 이미 독립적인 SQLite 사용 중, 무관
- `CHOI/locationAgent_sang/` — 이미 독립적인 SQLite 사용 중, 무관
- 프론트엔드 코드 전체 — DB와 직접 통신하지 않음

---

## 5. 마이그레이션 절차 (참고)

작업 순서는 다음과 같으며, 총 1~2일 예상.

```
Day 1
 ├── Oracle DB 스키마 + 데이터 덤프 (ora2pg 도구 사용)
 ├── Azure PostgreSQL Flexible Server 생성
 ├── Private Endpoint 설정 (Container Apps VNet 연결)
 └── 데이터 로드 및 row count 검증

Day 2
 ├── 코드 수정 (drvier 교체 + SQL 문법)
 ├── .env 업데이트
 ├── 로컬 테스트
 └── 스테이징 → 프로덕션 전환
```

---

## 6. 결론 및 권장사항

### 최종 권장: **Azure PostgreSQL Flexible Server**

> 월 $30, 1~2일 작업으로 아래를 모두 해결할 수 있습니다.

**해결되는 문제:**
- [x] 팀원 PC 종료 시 서비스 중단
- [x] DB 쿼리 속도 5~50배 향상
- [x] 팀원 로컬 Oracle 설치 의존 제거
- [x] 자동 백업 및 장애 복구
- [x] 코드에 하드코딩된 로컬 IP 제거

**남는 과제:**
- Oracle VM 옵션(코드 변경 최소)도 동일 구조 문제를 해결하므로, 코드 변경 여력이 없다면 일시적 대안으로 고려 가능
- Oracle Cloud 무료 옵션은 비용 절감이 필요하다면 검토 가능 (단, 크로스 클라우드 운영 복잡성 감수 필요)

---

*이 문서에 대한 질문이나 이견이 있으면 팀 채널에서 논의해주세요.*
