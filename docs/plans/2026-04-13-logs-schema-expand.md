# /api/v1/logs queries 스키마 확장 — signoff_ms·verdict.issues 노출

## Context

- handoff 2026-04-13-tc14-rerun의 next#1 (MED)
- 현재 `/api/v1/logs?type=queries` 응답은 `signoff_ms` 미포함, first-pass approved 건은 `verdict.issues`(low severity 경고) 관찰 채널 없음
- step2 handoff에서 주장된 `signoff_ms=0` 실측은 이 엔드포인트에서 나올 수 없었음 — 스키마 부재 확인
- 관찰 가시성 확보로 "low severity 가시화"(세션 C frontend severity 배지) 및 chat signoff 실행 확인의 근거 제공

## 변경 파일

| 파일 | 변경 |
|------|------|
| [backend/logger.py](backend/logger.py) | `log_query`에 `signoff_ms: int`, `final_verdict: dict \| None` kwarg 추가 → record에 `signoff_ms`, `verdict` 필드로 기록 |
| [backend/orchestrator.py](backend/orchestrator.py) | approved 반환 dict 2곳(비스트림 L157, 스트림 L378)에 `final_verdict=verdict` 추가. escalated 경로는 기존 `rejection_history`로 이미 노출되므로 변경 없음 |
| [backend/api_server.py](backend/api_server.py) | `log_query` 호출 2곳(L378, L542)에서 `signoff_ms=result.get("signoff_ms", 0)`, `final_verdict=result.get("final_verdict")` 전달 |
| [backend/tests/test_logger_rejection_history.py](backend/tests/test_logger_rejection_history.py) | 기존 테스트에 신규 필드 회귀 추가 또는 별도 `test_logger_signoff_ms.py` 신설 |

## 재사용

- `logger.py:_format_rejection_history`의 `verdict.issues` 정규화 로직 그대로 사용 가능 (code/severity/reason 추출). `final_verdict` 기록 시 동일 정규화 재사용해서 스키마 통일
- `log_formatter.py`는 CLI 출력 쪽이므로 이번 범위 밖

## 스키마 (확정)

queries.jsonl 엔트리에 다음 필드 추가:

```json
{
  "signoff_ms": 891,
  "final_verdict": {
    "approved": true,
    "grade": "A",
    "passed": ["..."],
    "issues": [{"code": "...", "severity": "low", "reason": "..."}],
    "warnings": [{"code": "...", "reason": "..."}]
  }
}
```

- signoff 생략(is_partial 등) 시 `signoff_ms=0`, `final_verdict=null`
- escalated는 `final_verdict=null` (마지막 verdict은 `rejection_history[-1]`)

## 검증

1. **ruff**: `.venv/bin/ruff check --fix backend/ && .venv/bin/ruff format backend/`
2. **pytest**: `cd backend && .venv/bin/pytest tests/test_logger_rejection_history.py tests/test_signoff_*.py -x`
3. **로컬 API smoke**:
   - `.venv/bin/python3 api_server.py` 기동
   - `curl -X POST localhost:8000/api/v1/query -d '{"question":"테스트"}'`
   - `curl localhost:8000/api/v1/logs?type=queries&limit=1` → 응답에 `signoff_ms`, `final_verdict` 확인
4. **PR 생성**: `fix/park-logs-schema-signoff` 브랜치, Test Plan에 위 3단계 체크박스

## 세션 외

- 프론트엔드 severity 배지(세션 C) — 별도 세션. 이번 PR은 백엔드 스키마 확장만
- ChatAgent 인젝션 pytest (next#2) — 별도 세션
- `log_formatter.py` CLI 포맷터 확장 — 필요 시 후속 PR
