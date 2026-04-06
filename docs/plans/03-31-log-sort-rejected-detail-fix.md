# 로그 정렬 오류 및 거부 이력 빈 상세 수정 플랜

## Context

프론트엔드 로그 뷰어(/dev/logs)에서 두 가지 버그 수정이 필요하다.

1. **로그 시간순 정렬 오류**: 최신 질의가 맨 위에 오지 않고 순서가 뒤섞임
2. **거부 이력 상세 내용 빈 출력**: "거부 이력" 탭에서 항목을 펼치면 내용이 공란

---

## 버그 1: 타임스탬프 혼재로 인한 정렬 오류

### 근본 원인

`integrated_PARK/logger.py` line 84의 `_now_iso()`:
```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()
```
`.astimezone()`이 서버 로컬 타임존으로 변환하므로 Azure Container Apps 환경에서 컨테이너마다 타임존이 달라 일부는 `+09:00`(KST), 일부는 `+00:00`(UTC)로 기록됨.

`integrated_PARK/log_formatter.py` line 235의 정렬:
```python
entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
```
문자열 비교로 정렬하므로 혼재 타임존에서 오작동: `"T12:00...+09:00"` 문자열이 `"T08:49...+00:00"`보다 크지만 실제 UTC로는 `12:00 KST = 03:00 UTC`로 더 이른 시각임.

### 수정 내용

**파일 1: `integrated_PARK/logger.py` line 84**
- `.astimezone()` 제거 → 항상 UTC로 출력
```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

**파일 2: `integrated_PARK/log_formatter.py`**
- `_ts_sort_key` 헬퍼 함수 추가 (기존 `_load_jsonl` 함수 앞):
```python
def _ts_sort_key(entry: dict):
    ts = entry.get("ts", "")
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)
```
- line 209 (`format_logs`) 및 line 235 (`load_entries_json`) 두 곳의 sort 호출 교체:
```python
entries.sort(key=_ts_sort_key, reverse=True)
```
`datetime.fromisoformat()`은 Python 3.12에서 `+09:00`/`+00:00` 모두 aware datetime으로 파싱하므로 레거시 데이터도 소급 수정됨.

---

## 버그 2: 거부 이력 상세 내용 빈 출력

### 근본 원인

과거 배포본에서 signoff 검증 결과가 정상 파싱되지 않아 아래와 같은 레거시 항목이 Blob Storage에 존재:
```json
{ "attempt": 1, "approved": null, "grade": "", "passed": [], "warnings": [], "issues": [], "retry_prompt": "" }
```
`LogTable.jsx`는 `rejHist.length > 0`이면 섹션을 렌더링하지만, 세 배열이 모두 비어 있고 `retry_prompt`도 없어 펼쳤을 때 내용이 공란.

### 수정 내용

**파일 3: `frontend/src/components/LogTable.jsx`** (lines 179–202, 확장 패널 내부)

기존 세 조건부 블록(`warnings.map`, `issues.map`, `retry_prompt`) 뒤에 폴백 메시지 추가:
```jsx
{(a.warnings || []).length === 0 &&
 (a.issues || []).length === 0 &&
 !a.retry_prompt && (
  <div className="text-muted-foreground text-center py-2">
    상세 정보가 없는 이력입니다.
  </div>
)}
```

---

## 수정 대상 파일 목록

| 파일 | 변경 위치 | 내용 |
|------|-----------|------|
| `integrated_PARK/logger.py` | line 84 | `.astimezone()` 제거 |
| `integrated_PARK/log_formatter.py` | ~line 43 신규 + line 209 + line 235 | `_ts_sort_key` 헬퍼 추가, sort 호출 2곳 교체 |
| `frontend/src/components/LogTable.jsx` | lines 179–202 내부 (~5줄 추가) | 빈 거부 이력 폴백 메시지 추가 |

---

## 검증 방법

```bash
# 1. 백엔드 정렬 확인
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=20" \
  | python3 -c "import json,sys; [print(e['ts']) for e in json.load(sys.stdin)['entries']]"
# → ts 값들이 내림차순(최신→과거) 정렬되어야 함

# 2. 거부 이력 탭 확인
# 프론트엔드 실행 후 /dev/logs → "거부 이력" 탭 → 항목 클릭
# → "상세 정보가 없는 이력입니다." 표시되어야 함 (빈 항목의 경우)
```
