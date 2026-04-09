# PR #244 리뷰 피드백 수정 계획

## Context

PR #244 (`feat: 성능 통계 API + 분석 스크립트`) 리뷰에서 발견된 이슈 6건 중 4건을 수정한다.

- #1 (percentile): Nit — 이번에는 스킵 (현재 구현이 대시보드 용도에 충분)
- #2 (전체 로그 메모리 로드): 현재 캐시로 커버됨 — 추후 개선
- #3 (ISO 문자열 TZ): KST 통일 확인됨 — 로그 한번 가져와서 검증만
- #5 (의존성): `requests`, `python-dotenv` 모두 requirements.txt에 존재 — 조치 불필요

## 스킵 항목 상세

### #1 (percentile) — 스킵 사유

현재 `_percentile`은 nearest-rank 방식으로, 보간(interpolation) 없이 정렬된 배열에서 인덱스를 직접 취한다.
`statistics.quantiles()`는 보간을 적용하여 더 정확한 값을 산출하지만, 차이가 유의미한 건 **샘플 수가 적을 때**(n < ~20)뿐이다.
성능 대시보드에서 표시하는 p50/p90은 대략적 추세 파악 용도이므로, nearest-rank로 충분하다.
또한 `statistics.quantiles()`는 Python 3.8+에서만 사용 가능하고, 반환 형태가 달라 헬퍼를 다시 래핑해야 하므로 변경 대비 이득이 적다.

### #2 (전체 로그 메모리 로드) — 현재 상태 설명

`/api/v1/stats`는 매 요청마다 `load_entries_json(limit=0)`을 호출하여 **전체 로그를 메모리에 로드**한다.
그러나 `log_formatter.py`의 `_LOG_CACHE`가 `{log_type: (expires_at, entries)}` 구조로 60초 TTL 캐시를 제공하므로,
60초 내 반복 요청은 디스크 I/O 없이 캐시된 리스트를 반환한다.

**현재 괜찮은 이유**: 로그가 수백~천 건 수준이고, 캐시 덕분에 동일 60초 윈도우 내에서는 파싱이 1회만 발생.
**추후 리스크**: 로그가 만 건 이상으로 늘어나면 (1) 캐시 미스 시 전체 파싱 비용, (2) 메모리 상주량이 문제될 수 있다.
이 시점에서는 `hours` 파라미터 기반 서버사이드 필터링 또는 캐시 키 분리가 필요하나, 현재 규모에서는 과잉 최적화.

## 수정 대상

### Fix 1: `error_rate` 분모 수정 (#4)

**파일**: `integrated_PARK/api_server.py` (line ~695-697)

현재:

```python
total = len(queries) + len(errors)
"error_rate": round(len(errors) / total, 4) if total else 0.0
```

수정:

```python
"error_rate": round(len(errors) / len(queries), 4) if queries else 0.0
```

`total`은 요약 카운트로 유지하되, `error_rate`는 쿼리 대비 에러 비율로 변경.

### Fix 2: `"T99"` 매직 스트링 제거 (#6)

**파일**: `integrated_PARK/scripts/analyze_logs.py` (line ~211)

현재:

```python
result = [e for e in result if e.get("ts", "") < until + "T99"]
```

수정 — 날짜 +1일 방식:

```python
from datetime import date, timedelta
next_day = (date.fromisoformat(until) + timedelta(days=1)).isoformat()
result = [e for e in result if e.get("ts", "") < next_day]
```

`datetime`과 `timedelta`는 이미 import됨. `date`만 추가.

### Fix 3: TZ 검증 (#3)

백엔드 로그를 가져와서 `ts` 필드의 타임존 형식이 일관적인지 확인.

```bash
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=5" | python3 -m json.tool | grep '"ts"'
```

결과: 모든 `ts`가 `+00:00` (UTC)로 통일 — 문자열 비교 안전.

## 수정 파일 요약

| 파일                                   | 변경                                       |
|----------------------------------------|--------------------------------------------|
| `integrated_PARK/api_server.py`        | `error_rate` 분모를 `len(queries)`로 변경  |
| `integrated_PARK/scripts/analyze_logs.py` | `"T99"` → 날짜+1일 방식, `date` import 추가 |

## 검증

1. `python3 -c "import api_server"` — import 정상 확인
2. `python3 -c "from scripts.analyze_logs import filter_by_date"` — import 확인
3. 백엔드 배포 후: `curl /api/v1/stats?hours=24` → `error_rate` 값이 `errors/queries` 비율인지 확인
