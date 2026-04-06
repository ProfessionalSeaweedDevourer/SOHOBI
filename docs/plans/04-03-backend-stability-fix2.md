# 백엔드 안정성 2차 수정 플랜

## Context

이전 세션에서 DB 풀 고갈(maxconn 5→20), 쿼리 타임아웃, 세션 LRU, matplotlib Lock, Kernel 싱글톤을 수정했다.
이번 플랜은 그 이후에도 남아 있는 리소스 누수·타임아웃 공백을 제거한다.

발견된 근본 문제:
1. `finance_db.DBWork`가 매 재무 쿼리마다 raw 커넥션을 새로 열어 PostgreSQL 연결 한도 소진 위험
2. `baseDAO._pool`에 `connect_timeout`/`statement_timeout`이 없어 DAO 쿼리 무한 블록 가능
3. 에이전트 6곳의 LLM 호출에 타임아웃 없음 — Azure OpenAI 지연 시 AsyncIO 태스크 스택
4. 예외 무시(`except Exception: pass`) 2곳에서 운영 중 장애 원인 추적 불가

---

## 커밋 1: fix(db): DBWork 풀 통합, baseDAO 타임아웃 추가

### `integrated_PARK/db/dao/baseDAO.py` — 풀 생성 파라미터 (줄 19-28)
`_get_pool()` 안 `ThreadedConnectionPool(...)` 에 2줄 추가:
```python
connect_timeout=10,                    # 신규
options="-c statement_timeout=15000",  # 신규 (repository.py와 동일하게 맞춤)
```

### `integrated_PARK/db/finance_db.py` — 전체 재작성
`DBWork`를 `BaseDAO` 상속으로 전환. `_get_connection()`·`import os`·`import psycopg2`·`load_dotenv()` 제거.
RealDictCursor 반환 형태에 맞춰 `row["tot_sales_amt"]` / `row["avg"]` 키 접근.
```python
import logging
from db.dao.baseDAO import BaseDAO

logger = logging.getLogger(__name__)

class DBWork(BaseDAO):
    def get_sales(self, region: list, industry: str) -> list:
        if not region or not industry:
            return [17000000]
        placeholders = ",".join(["%s"] * len(region))
        sql = f"SELECT tot_sales_amt FROM sangkwon_sales WHERE adm_cd IN ({placeholders}) AND svc_induty_cd = %s"
        conn, cur = self._db_con()
        try:
            cur.execute(sql, region + [industry])
            rows = cur.fetchall()
            return [row["tot_sales_amt"] for row in rows] if rows else [17000000]
        except Exception as e:
            logger.warning("DBWork.get_sales 실패 region=%s industry=%s: %s", region, industry, e)
            return [17000000]
        finally:
            self._close(conn, cur)

    def get_average_sales(self) -> list:
        sql = "SELECT ROUND(AVG(tot_sales_amt)) AS avg FROM sangkwon_sales WHERE svc_induty_cd LIKE 'CS10%'"
        conn, cur = self._db_con()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            return [row["avg"]] if row and row["avg"] is not None else [170000000]
        except Exception as e:
            logger.warning("DBWork.get_average_sales 실패: %s", e)
            return [170000000]
        finally:
            self._close(conn, cur)
```
**주의:** `baseDAO._pool`(maxconn=10)을 `seoulRtmsDAO` 등과 공유하게 된다. 재무 동시 요청이 증가하면 `maxconn`을 15-20으로 올리는 별도 작업 고려.

---

## 커밋 2: fix(agents): LLM 호출 asyncio.wait_for 타임아웃 적용

### 공통 패턴
모든 `service.get_chat_message_content(...)` 호출을 `asyncio.wait_for(..., timeout=N)` 으로 래핑.
Python 3.11+ 에서 `asyncio.TimeoutError ⊂ Exception` 이므로 기존 `except Exception` 블록이 있는 곳은 자동 처리.

타임아웃 정책: router 30초 / 에이전트 60초 / chat 30초.

### `integrated_PARK/domain_router.py`
- 상단에 `import asyncio` 추가 (현재 없음)
- 줄 57 래핑:
```python
result = await asyncio.wait_for(
    chat_service.get_chat_message_content(chat_history=history, settings=settings),
    timeout=30.0,
)
```
기존 `except Exception: return _FALLBACK`이 TimeoutError도 처리함.

### `integrated_PARK/agents/finance_agent.py`
- 상단에 `import asyncio` 추가 (현재 없음)
- 줄 126 (`_call_llm` 1차), 줄 186 (`_call_llm_with_history` 1차), 줄 195 (재시도) 3곳 래핑:
```python
result = await asyncio.wait_for(
    service.get_chat_message_content(history, settings=settings),
    timeout=60.0,
)
```

### `integrated_PARK/agents/location_agent.py`
- `import asyncio` 이미 존재
- 줄 255 (1차), 줄 268 (재시도) 래핑:
```python
result = await asyncio.wait_for(
    service.get_chat_message_content(history, settings=settings),
    timeout=60.0,
)
```

### `integrated_PARK/agents/legal_agent.py`
- 상단에 `import asyncio`, `import logging`, `logger = logging.getLogger(__name__)` 추가 (현재 전무)
- 줄 120의 직접 노출 호출을 try/except로 감싸고 래핑:
```python
try:
    response = await asyncio.wait_for(
        service.get_chat_message_content(history, settings=settings, kernel=self._kernel),
        timeout=60.0,
    )
except asyncio.TimeoutError:
    logger.warning("LegalAgent LLM 타임아웃 (60초)")
    raise ValueError("AI 응답 생성 중 타임아웃이 발생했습니다. 잠시 후 다시 시도해 주세요.")
except Exception as e:
    logger.error("LegalAgent LLM 호출 실패: %s", e)
    raise ValueError(f"AI 응답 생성 중 오류가 발생했습니다: {e}") from e
return str(response)
```

### `integrated_PARK/agents/admin_agent.py`
- legal_agent와 동일 구조. 상단에 `import asyncio`, `import logging`, `logger` 추가.
- 줄 120 동일 패턴 적용, except 메시지는 "AdminAgent LLM 타임아웃".

### `integrated_PARK/agents/chat_agent.py`
- 상단에 `import asyncio`, `import logging`, `logger = logging.getLogger(__name__)` 추가.
- 줄 89 래핑. `ValueError` raise 대신 사용자 메시지 return:
```python
try:
    response = await asyncio.wait_for(
        service.get_chat_message_content(history, settings=settings, kernel=self._kernel),
        timeout=30.0,
    )
except asyncio.TimeoutError:
    logger.warning("ChatAgent LLM 타임아웃 (30초)")
    return "응답 생성에 시간이 걸리고 있습니다. 잠시 후 다시 시도해 주세요."
except Exception as e:
    logger.error("ChatAgent LLM 호출 실패: %s", e)
    return "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
return str(response)
```

---

## 커밋 3: fix(logging): 예외 무시 pass → logger.warning

### `integrated_PARK/api_server.py` — `_extract_and_save()` (줄 173)
`api_server.py`에 `import asyncio`는 이미 있으나 모듈 레벨 logger 없음.
상단(줄 10 아래)에 추가:
```python
import logging
_logger = logging.getLogger("sohobi.api")
```
`_extract_and_save()` except 수정:
```python
except Exception as e:
    _logger.warning("재무 변수 백그라운드 추출 실패 sid=%s: %s", sid, e)
```

### `integrated_PARK/db/dao/baseDAO.py` — `_close()` (줄 41-50)
`logger`는 줄 10에 이미 선언됨. 두 except 블록만 수정:
```python
except Exception as e:
    logger.warning("[BaseDAO] 커서 닫기 실패: %s", e)
...
except Exception as e:
    logger.warning("[BaseDAO] 커넥션 풀 반납 실패 — 누수 가능성: %s", e)
```

---

## 수정 파일 목록

| 커밋 | 파일 | 변경 범위 |
|------|------|----------|
| 1 | `db/dao/baseDAO.py` | 풀 생성 +2줄, _close 로깅 |
| 1 | `db/finance_db.py` | 전체 재작성 (62→40줄) |
| 2 | `domain_router.py` | import 추가, 줄 57 래핑 |
| 2 | `agents/finance_agent.py` | import 추가, 3곳 래핑 |
| 2 | `agents/location_agent.py` | 2곳 래핑 |
| 2 | `agents/legal_agent.py` | import 3개 추가, 줄 120 래핑 |
| 2 | `agents/admin_agent.py` | import 3개 추가, 줄 120 래핑 |
| 2 | `agents/chat_agent.py` | import 3개 추가, 줄 89 래핑 |
| 3 | `api_server.py` | import+logger 추가, 줄 173 수정 |

---

## 검증

```bash
# 구문 검증 (커밋별)
cd integrated_PARK
.venv/bin/python3 -c "from db.finance_db import DBWork; from db.dao.baseDAO import BaseDAO; assert issubclass(DBWork, BaseDAO)"
.venv/bin/python3 -c "import ast; [ast.parse(open(f).read()) for f in ['agents/finance_agent.py','agents/legal_agent.py','agents/admin_agent.py','agents/chat_agent.py','domain_router.py']]"

# API 동작 확인 (배포 후)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남 카페 상권 분석해줘"}'
```

타임아웃 검증: Azure OpenAI 엔드포인트를 존재하지 않는 URL로 임시 변경 후 요청 → 30/60초 이내 에러 응답 확인 (기존에는 10분 대기).
