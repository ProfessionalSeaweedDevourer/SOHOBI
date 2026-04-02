# 상권분석 에이전트/플러그인 테스트 & 버그 수정

**작성일**: 2026-04-01  
**최종 업데이트**: 2026-04-02 (PostgreSQL 마이그레이션 반영, Issue-4·5 수정, 추가 버그 3건·테스트 3건)  
**대상 파일**: `integrated_PARK/agents/location_agent.py`, `integrated_PARK/plugins/location_plugin.py`

---

## 수정된 버그 / 이슈 (총 8건)

### Bug-1: `location_plugin.py` 반환 타입 불일치
- **위치**: [location_plugin.py:49,70](../../integrated_PARK/plugins/location_plugin.py)
- **증상**: `analyze_commercial_area` / `compare_commercial_areas`가 `-> str` 주석과 달리 dict를 반환 → SK Plugin 직렬화 오류
- **수정**: `json.dumps(result, ensure_ascii=False)` 로 str 변환 후 반환

### Bug-2: `_call_llm` content_filter 재시도 시 user_msg 누락
- **위치**: [location_agent.py:163~169](../../integrated_PARK/agents/location_agent.py)
- **증상**: content_filter 예외 발생 시 `ChatHistory(system_message=safe_sys)` 만 생성 → user 메시지 없이 LLM 호출 → 컨텍스트 없는 응답
- **수정**: `safe_history.add_user_message(user_msg)` 추가

### Bug-3: `analyze()` breakdown 키 오류 → KeyError
- **위치**: [location_agent.py:266,268](../../integrated_PARK/agents/location_agent.py)
- **증상**: `b["trdar_name"]` 접근 → repository breakdown의 실제 키는 `"adm_name"` → KeyError로 정상 분석 불가
- **수정**: `"trdar_name"` → `"adm_name"` 으로 수정

### Issue-4: psycopg2 동기 호출이 asyncio 이벤트 루프 블로킹 (PostgreSQL 마이그레이션 후 발생)
- **위치**: [location_agent.py](../../integrated_PARK/agents/location_agent.py) — `analyze()`, `compare()`
- **증상**: `psycopg2`는 synchronous-only 드라이버. FastAPI 이벤트 루프에서 직접 호출 시 DB I/O 동안 모든 요청 중단
- **수정**: `asyncio.to_thread()` + `asyncio.gather()`로 병렬 비동기화
  - `analyze()`: `get_sales` + `get_store_count` 병렬 실행, `_run_agent` + `get_similar_locations` 병렬 실행
  - `compare()`: 전 지역 `get_sales` + `get_store_count`를 `asyncio.gather()`로 일괄 병렬 실행

### Issue-6: `get_similar_locations()` exclude 필터 후 빈 배열 → IndexError
- **위치**: [repository.py:650](../../integrated_PARK/db/repository.py)
- **증상**: `rows = [r for r in rows if r["adm_cd"] not in exclude_codes]` 후 rows가 빈 배열이 되면 `sorted([])[0]` → IndexError
- **수정**: 필터 직후 `if not rows: return []` 가드 추가

### Issue-7: `_get_pool()` 멀티스레드 초기화 레이스 컨디션
- **위치**: [repository.py:402](../../integrated_PARK/db/repository.py)
- **증상**: `asyncio.to_thread()`로 여러 스레드가 동시에 `_pool is None` 체크 → 풀 이중 생성 가능
- **수정**: `threading.Lock()` 기반 double-checked locking 적용

### Issue-8: 연결 풀 고갈 시 PoolError 미처리 → 사용자에게 노출
- **위치**: [repository.py:410](../../integrated_PARK/db/repository.py)
- **증상**: `maxconn=5` 초과 시 `psycopg2.pool.PoolError`가 그대로 전파
- **수정**: `_connect()`에서 `PoolError` catch → `RuntimeError("DB 연결을 확보할 수 없습니다.")` 변환

### Issue-9: LLM 실패가 `generate_draft()` 밖으로 전파 → FastAPI 500
- **위치**: [location_agent.py:415](../../integrated_PARK/agents/location_agent.py)
- **증상**: `_run_agent()` ValueError가 `analyze()`를 거쳐 `generate_draft()`까지 전파 → HTTP 500
- **수정**: `generate_draft()` 내 `analyze()`/`compare()` 호출을 `try/except (ValueError, RuntimeError)`로 감싸 안내 메시지 반환

### Issue-5: `_extract_params` 정규식이 LLM 앞문장 처리 실패
- **위치**: [location_agent.py:190](../../integrated_PARK/agents/location_agent.py)
- **증상**: LLM이 "설명\n\`\`\`json\n{...}\n\`\`\`" 형태 반환 시 `re.sub`이 앞문장을 제거 못함 → `json.loads()` 실패 → 폴백 → "지역명과 업종을 명시해 주십시오" 오답
- **수정**: `re.sub` → `re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)` 로 코드펜스 내부 JSON 직접 추출

---

## 테스트 파일

**생성 파일**: `integrated_PARK/tests/test_location_agent.py` (19개 테스트)

| ID | 클래스 | 설명 |
|----|--------|------|
| T-LA-01 | TestExtractParams | 정상 JSON 파싱 |
| T-LA-02 | TestExtractParams | \`\`\`json 코드블록 래핑 제거 |
| T-LA-03 | TestExtractParams | LLM JSON 실패 시 기본값 폴백 |
| T-LA-04 | TestGenerateDraftGuard | locations 빈 배열 → 안내 메시지 |
| T-LA-05 | TestGenerateDraftGuard | business_type 빈 문자열 → 안내 메시지 |
| T-LA-06 | TestGenerateDraftGuard | prior_history=None 정상 처리 |
| T-LA-07 | TestAnalyze | 미지원 업종 → 안내 메시지 반환 |
| T-LA-08 | TestAnalyze | DB 데이터 없음 → 안내 메시지 반환 |
| T-LA-09 | TestAnalyze | **Bug-3** 재현: trdar_name KeyError 없이 정상 반환 |
| T-LA-10 | TestAnalyze | store_count=0 ZeroDivisionError 없음 |
| T-LA-11 | TestCompare | 전체 지역 DB 미조회 → 안내 메시지 |
| T-LA-12 | TestCompare | 일부 지역만 조회 → 조회된 지역으로 결과 생성 |
| T-LA-13 | TestCallLlm | **Bug-2** 재현: content_filter 재시도 시 user 메시지 포함 확인 |
| T-LA-14 | TestCallLlm | LLM 빈 응답 → ValueError 발생 |
| T-LA-15 | TestPlugin | **Bug-1** 재현: analyze_commercial_area 반환값이 str인지 확인 |
| T-LA-16 | TestPlugin | compare_commercial_areas 쉼표 파싱 |
| T-LA-17 | TestPlugin | 쉼표+공백 구분자 처리 |
| T-LA-18 | TestAsyncioAndRegex | **Issue-4** 재현: analyze() DB 호출이 asyncio.to_thread() 경유하는지 검증 |
| T-LA-19 | TestAsyncioAndRegex | **Issue-5** 재현: LLM 앞문장+JSON 코드블록 정상 파싱 검증 |
| T-LA-20 | TestEdgeCases | compare() 미지원 업종 → 안내 메시지 (T-LA-07의 compare 대응) |
| T-LA-21 | TestEdgeCases | generate_draft() retry_prompt 있을 때 LLM 3회 호출 검증 |
| T-LA-22 | TestEdgeCases | **Issue-9** 재현: LLM 실패 시 ValueError 전파 아닌 안내 메시지 반환 |

---

## PostgreSQL 마이그레이션 영향

main 브랜치 커밋 949d10a에서 DB가 Oracle → Azure PostgreSQL Flexible Server로 변경됨.

| 항목 | Oracle (이전) | PostgreSQL (현재) |
|------|--------------|------------------|
| 드라이버 | `oracledb==2.5.0` | `psycopg2-binary==2.9.9` |
| SQL 바인딩 | `:1, :2` | `%s, %s` |
| 테이블명 | `SANGKWON_SALES` | `sangkwon_sales` |
| 연결 해제 | 자동 | `_release(conn)` 명시 |

**기존 테스트 영향**: 없음 — 모든 테스트가 `CommercialRepository`를 `MagicMock()`으로 대체.  
단, `psycopg2-binary==2.9.9`가 venv에 설치되어 있어야 모듈 import가 성공함.

---

## 테스트 실행

```bash
cd integrated_PARK
# psycopg2-binary 미설치 시 먼저 설치
python -m pip install psycopg2-binary==2.9.9

python -m pytest tests/test_location_agent.py -v
# 22 passed (Azure LLM·PostgreSQL DB 불필요, mock 기반)
```

---

## 결과 요약

- **수정 파일**:
  - `agents/location_agent.py` (Bug-2, Bug-3, Issue-4, Issue-5, Issue-9)
  - `plugins/location_plugin.py` (Bug-1)
  - `db/repository.py` (Issue-6, Issue-7, Issue-8)
- **신규 파일**: `tests/test_location_agent.py`
- **테스트 결과**: 22/22 passed
