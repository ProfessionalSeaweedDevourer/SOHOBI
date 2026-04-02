# 상권분석 에이전트/플러그인 테스트 & 버그 수정

**작성일**: 2026-04-01  
**대상 파일**: `integrated_PARK/agents/location_agent.py`, `integrated_PARK/plugins/location_plugin.py`

---

## 발견된 버그 (총 3건)

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

---

## 테스트 파일

**생성 파일**: `integrated_PARK/tests/test_location_agent.py` (17개 테스트)

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

---

## 테스트 실행

```bash
cd integrated_PARK
python3 -m pytest tests/test_location_agent.py -v
# 17 passed (Azure LLM·Oracle DB 불필요, mock 기반)
```

---

## 결과 요약

- **수정 파일**: `agents/location_agent.py` (Bug-2, Bug-3), `plugins/location_plugin.py` (Bug-1)
- **신규 파일**: `tests/test_location_agent.py`
- **테스트 결과**: 17/17 passed
