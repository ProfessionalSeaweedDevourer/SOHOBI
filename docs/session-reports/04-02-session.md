# 세션 리포트 — 2026-04-02

## 작업 목표

`integrated_PARK/agents/location_agent.py` / `plugins/location_plugin.py` / `db/repository.py`
상권분석 에이전트 코드에 대한 체계적 테스트 작성, 버그 발굴 및 수정.

추가 배경: main 브랜치에서 DB가 **Oracle → Azure PostgreSQL Flexible Server**로 교체(커밋 `949d10a`)되어
rebase 반영 후 영향 분석도 병행 수행.

---

## 발견 및 수정한 문제 (총 8건)

### Bug-1 — Plugin 반환 타입 불일치 → SK 직렬화 오류

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/plugins/location_plugin.py` L49, L70 |
| 증상 | `analyze_commercial_area` / `compare_commercial_areas`가 `dict`를 반환 → Semantic Kernel이 `str`을 기대하므로 오케스트레이터에서 직렬화 오류 발생 |
| 수정 | `json.dumps(result, ensure_ascii=False)` 로 `str` 변환 후 반환 |

---

### Bug-2 — content_filter 재시도 시 사용자 메시지 누락

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/agents/location_agent.py` L163~169 |
| 증상 | Azure OpenAI content_filter 예외 발생 시 재시도 `ChatHistory`에 시스템 메시지만 포함 → user 메시지 없이 LLM 재호출 → 컨텍스트 없는 응답 |
| 수정 | `safe_history.add_user_message(user_msg)` 추가 |

---

### Bug-3 — breakdown 키 오류 → KeyError로 정상 분석 불가

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/agents/location_agent.py` L266, L268 |
| 증상 | `b["trdar_name"]` 접근 → 실제 repository 반환 키는 `"adm_name"` → 정상 입력에서도 항상 KeyError 발생 |
| 수정 | `"trdar_name"` → `"adm_name"` 으로 변경 |

---

### Issue-4 — psycopg2 동기 호출이 FastAPI 이벤트 루프 블로킹

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/agents/location_agent.py` — `analyze()`, `compare()` |
| 발생 원인 | main 브랜치 PostgreSQL 마이그레이션(`psycopg2`는 동기 전용 드라이버) |
| 증상 | DB 쿼리 실행 동안(건당 1~3초) FastAPI 이벤트 루프 전체가 멈춤 → 동시 사용자 모든 요청 중단 |
| 수정 | `asyncio.to_thread()` + `asyncio.gather()`로 비동기화 및 병렬 실행 |

**수정 효과**

| 호출 | 수정 전 | 수정 후 |
|------|---------|---------|
| `analyze()` DB 2건 | 직렬 ~2s | 병렬 ~1s |
| `analyze()` LLM + 유사상권 | 직렬 ~5s | 병렬 ~3s |
| `compare()` 3개 지역 × 2쿼리 | 직렬 ~9s | 병렬 ~3s |

---

### Issue-5 — LLM 앞문장 포함 응답 시 JSON 파싱 실패 → 오답 반환

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/agents/location_agent.py` L190 |
| 증상 | LLM이 "설명\n\`\`\`json\n{...}\n\`\`\`" 형태로 반환 시 `re.sub`이 앞문장을 제거 못함 → `json.loads()` 실패 → 빈 값 폴백 → "지역명과 업종을 명시해 주십시오" 오답 |
| 수정 | `re.sub` → `re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)` 로 코드펜스 내부 JSON 직접 추출 |

---

### Issue-6 — `get_similar_locations()` exclude 필터 후 빈 배열 → IndexError

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/db/repository.py` L650 |
| 증상 | exclude 코드 필터 후 `rows`가 빈 배열이 되면 `sorted([])[0]` → IndexError → 유사 상권 조회 시 서버 크래시 |
| 수정 | 필터 직후 `if not rows: return []` 가드 추가 |

---

### Issue-7 — `_get_pool()` 멀티스레드 초기화 레이스 컨디션

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/db/repository.py` — `CommercialRepository._get_pool()` |
| 증상 | `asyncio.to_thread()`로 여러 스레드가 동시에 `_pool is None` 체크 → 서버 시작 직후 커넥션 풀이 이중 생성될 수 있음 |
| 수정 | `threading.Lock()` 기반 double-checked locking 적용 |

---

### Issue-8 & 9 — DB 풀 고갈 / LLM 실패 → HTTP 500 노출

| 항목 | 내용 |
|------|------|
| 파일 | `repository.py` `_connect()` / `location_agent.py` `generate_draft()` |
| 증상 | (8) `maxconn=5` 초과 시 `psycopg2.pool.PoolError`가 사용자에게 노출 (9) `_run_agent()` LLM 실패가 `generate_draft()` 밖으로 전파 → FastAPI HTTP 500 |
| 수정 | (8) `_connect()`에서 `PoolError` catch → `RuntimeError("DB 연결을 확보할 수 없습니다.")` 변환 (9) `generate_draft()`에 `try/except (ValueError, RuntimeError)` 추가 → 안내 메시지 반환 |

---

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `integrated_PARK/agents/location_agent.py` | Bug-2, Bug-3, Issue-4, Issue-5, Issue-9 |
| `integrated_PARK/plugins/location_plugin.py` | Bug-1 |
| `integrated_PARK/db/repository.py` | Issue-6, Issue-7, Issue-8 |

---

## PostgreSQL 마이그레이션 영향 분석

main 브랜치 커밋 `949d10a`에서 DB 드라이버 및 연결 방식 전면 교체.

| 항목 | Oracle (이전) | PostgreSQL (현재) |
|------|--------------|------------------|
| 드라이버 | `oracledb==2.5.0` | `psycopg2-binary==2.9.9` |
| SQL 바인딩 | `:1, :2` | `%s, %s` |
| 커넥션 풀 | `oracledb.create_pool()` | `psycopg2.pool.ThreadedConnectionPool` |
| 테이블명 | `SANGKWON_SALES` | `sangkwon_sales` (소문자) |
| 연결 해제 | 자동 | `_release(conn)` 명시 |

**주의**: `psycopg2-binary==2.9.9`가 venv에 설치되어 있어야 합니다.
`requirements.txt`에는 명시되어 있으나 이번 작업 시점에 미설치 상태였음 → 수동 설치로 해결.

```bash
cd integrated_PARK
python -m pip install psycopg2-binary==2.9.9
```

---

## 테스트 현황

**파일**: `integrated_PARK/tests/test_location_agent.py`  
**실행 방식**: mock 기반 — Azure LLM · PostgreSQL DB 연결 불필요

```bash
cd integrated_PARK
python -m pytest tests/test_location_agent.py -v
# 22 passed in 3.10s
```

| ID | 클래스 | 검증 내용 |
|----|--------|----------|
| T-LA-01 | TestExtractParams | 정상 JSON 파싱 |
| T-LA-02 | TestExtractParams | \`\`\`json 코드블록 래핑 제거 |
| T-LA-03 | TestExtractParams | LLM JSON 실패 → 기본값 폴백 |
| T-LA-04 | TestGenerateDraftGuard | locations 빈 배열 → 안내 메시지 |
| T-LA-05 | TestGenerateDraftGuard | business_type 빈 문자열 → 안내 메시지 |
| T-LA-06 | TestGenerateDraftGuard | prior_history=None 정상 처리 |
| T-LA-07 | TestAnalyze | 미지원 업종 → 안내 메시지 (DB 호출 없음) |
| T-LA-08 | TestAnalyze | DB 데이터 없음 → 안내 메시지 |
| T-LA-09 | TestAnalyze | **Bug-3** 재현: adm_name 키로 KeyError 없이 정상 반환 |
| T-LA-10 | TestAnalyze | store_count=0 → ZeroDivisionError 없음 |
| T-LA-11 | TestCompare | 전체 지역 DB 미조회 → 안내 메시지 |
| T-LA-12 | TestCompare | 일부 지역만 조회 → 조회된 지역으로 결과 생성 |
| T-LA-13 | TestCallLlm | **Bug-2** 재현: content_filter 재시도 시 user 메시지 포함 확인 |
| T-LA-14 | TestCallLlm | LLM 빈 응답 → ValueError 발생 |
| T-LA-15 | TestPlugin | **Bug-1** 재현: analyze_commercial_area 반환값 str 확인 |
| T-LA-16 | TestPlugin | compare_commercial_areas 쉼표 파싱 |
| T-LA-17 | TestPlugin | 쉼표+공백 구분자 처리 |
| T-LA-18 | TestAsyncioAndRegex | **Issue-4** 재현: DB 호출이 asyncio.to_thread() 경유 확인 |
| T-LA-19 | TestAsyncioAndRegex | **Issue-5** 재현: LLM 앞문장+JSON 코드블록 정상 파싱 |
| T-LA-20 | TestEdgeCases | compare() 미지원 업종 → 안내 메시지 (DB 호출 없음) |
| T-LA-21 | TestEdgeCases | retry_prompt 있을 때 LLM 3회 호출 검증 |
| T-LA-22 | TestEdgeCases | **Issue-9** 재현: LLM 실패 → ValueError 전파 아닌 안내 메시지 반환 |

---

## 참고 문서

- 상세 플랜: [`docs/plans/2026-04-01-location-agent-test-plan.md`](../plans/2026-04-01-location-agent-test-plan.md)
- 작업 브랜치: `CHOI2`
