# 플랜: location_agent Oracle DB 전환 (PARK 브랜치)

## Context

현재 `integrated_PARK`의 상권 에이전트는 13MB SQLite 파일(`commercial.db`)을 직접 읽는다.
CHOI/locationAgent_DB에는 팀 공용 Oracle DB 서버와 연결하는 최신 버전이 존재하며,
이를 기준으로 통합본을 교체해야 한다. 작업은 main을 손상시키지 않기 위해
PARK 브랜치에서 진행하며, 작업 전 PARK를 main 최신으로 동기화한다.

---

## 구조 차이 요약

| 항목 | integrated_PARK (현재) | CHOI/locationAgent_DB (신규) |
|------|----------------------|------------------------------|
| DB 드라이버 | `sqlite3` (stdlib) | `oracledb` 2.5.0 |
| 연결 방식 | per-query `sqlite3.connect()` | connection pool (min=2, max=5) |
| 테이블명 | `commercial_sales`, `commercial_store` | `SANGKWON_SALES`, `SANGKWON_STORE` |
| 지역 매핑 기준 | 상권명 문자열 (예: "홍대입구역(홍대)") | 행정동 코드 ADM_CD (예: "11440660") |
| `AREA_MAP` 값 타입 | `list[str]` (상권명) | `list[str]` (8자리 ADM_CD 코드) |
| `get_similar_locations()` 반환 키 | `trdar_name` | `adm_name` |
| 공개 인터페이스 | `get_sales`, `get_store_count`, `get_similar_locations`, `get_supported_*` | 동일 |
| 환경변수 | `COMMERCIAL_DB_PATH` | `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN` |

**location_agent.py 영향도:** 최소. 1곳만 깨짐:
- `agents/location_agent.py:268` — `s['trdar_name']` → `s['adm_name']`

---

## 단계별 작업

### Step 1: PARK 브랜치를 main으로 최신화

```bash
git checkout PARK
git merge main
# 충돌 시 해결 후 커밋
```

### Step 2: db/repository.py 교체

`integrated_PARK/db/repository.py` 전체를 `CHOI/locationAgent_DB/db/repository.py` 내용으로 교체.
- AREA_MAP: ADM_CD 기반 매핑으로 전환
- INDUSTRY_CODE_MAP: 동일 (코드값 같음)
- CommercialRepository: Oracle 커넥션 풀 + SANGKWON_SALES/STORE 쿼리

### Step 3: location_agent.py 부분 수정

`integrated_PARK/agents/location_agent.py:268`:
```python
# 변경 전
f"| {i+1} | {s['trdar_name']} | ..."
# 변경 후
f"| {i+1} | {s['adm_name']} | ..."
```

### Step 4: requirements.txt 업데이트

`integrated_PARK/requirements.txt`에 추가:
```
oracledb==2.5.0
```

### Step 5: 환경변수 추가 (.env — 커밋 금지)

팀 DB 서버 접속 정보를 `.env`에 추가:
```
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_DSN=host:port/service_name
```

`COMMERCIAL_DB_PATH` 변수는 더 이상 사용되지 않으므로 제거 가능.

---

## 주의 사항

- `integrated_PARK/db/commercial.db`는 그대로 유지 (main 브랜치용, git에 이미 포함)
- Oracle 드라이버 설치: `oracledb`는 Oracle Instant Client 없이도 thin mode로 작동
- `get_similar_locations()`의 반환 구조가 `adm_cd` 키를 추가 포함하나, location_agent.py는 이를 사용하지 않으므로 무해

---

## 수정 대상 파일

| 파일 | 작업 |
|------|------|
| `integrated_PARK/db/repository.py` | 전체 교체 (Oracle 버전으로) |
| `integrated_PARK/agents/location_agent.py` | 1줄 수정 (`trdar_name` → `adm_name`) |
| `integrated_PARK/requirements.txt` | `oracledb==2.5.0` 추가 |

---

## 검증

```bash
# Oracle 연결 확인
cd integrated_PARK && .venv/bin/python3 -c "
from db.repository import CommercialRepository
r = CommercialRepository()
print(r.get_sales('홍대', '카페', '20244'))
"

# API 서버 구동 후 curl 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "홍대 카페 분석해줘"}'
```
