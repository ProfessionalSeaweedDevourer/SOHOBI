# 작업 플랜: LogViewer 세션 ID · IP 수집 · 개인정보처리방침 정비

## Context

이전 세션에서 LogViewer 응답자 계정명 표시 + 사용자별 필터링 기능을 구현했으나 미커밋 상태. 이번 세션에서는 해당 변경을 커밋·PR 생성 후, 인수인계 문서에 정의된 3개 후속 작업을 순서대로 완료한다.

---

## 작업 0 — 이전 세션 변경 커밋 & PR 생성

**대상 파일 (7개, 이미 완성된 변경):**
- `integrated_PARK/logger.py`
- `integrated_PARK/session_store.py`
- `integrated_PARK/auth_router.py`
- `integrated_PARK/api_server.py`
- `frontend/src/api.js`
- `frontend/src/pages/LogViewer.jsx`
- `frontend/src/components/LogTable.jsx`

**커밋 메시지:** `feat: LogViewer 응답자 계정명 표시 및 사용자별 필터링`

**PR 생성 후** `gh pr list --head PARK --state open`으로 PR 번호 확인

---

## 작업 1 — LogViewer 세션 ID 표시 및 세션 기반 필터

### 1-1. `frontend/src/components/LogTable.jsx`

**EntryDetail 메타 영역**에 session_id 추가:
```jsx
{entry.session_id && (
  <span
    className="text-muted-foreground font-mono text-xs truncate max-w-[160px] cursor-pointer hover:text-foreground"
    title={entry.session_id}
    onClick={() => navigator.clipboard.writeText(entry.session_id)}
  >
    🔗 {entry.session_id.slice(0, 8)}…
  </span>
)}
```

**목록 항목 버튼**에 session_id 앞 8자 표시 (사용자명 아래 부 정보로).

### 1-2. `frontend/src/pages/LogViewer.jsx`

상태 추가: `const [sessionFilter, setSessionFilter] = useState("");`

필터 UI (사용자 드롭다운 옆):
```jsx
<input
  type="text"
  placeholder="세션 ID 검색..."
  value={sessionFilter}
  onChange={(e) => setSessionFilter(e.target.value)}
  className="text-xs rounded-lg px-2 py-1 border border-[var(--border)] bg-[var(--card)] text-foreground w-40"
/>
```

displayEntries 필터링에 AND 조건 추가:
```javascript
const displayEntries = entries.filter((e) =>
  (!selectedUser || e.user_id === selectedUser) &&
  (!sessionFilter || e.session_id?.includes(sessionFilter))
);
```

### 1-3. `integrated_PARK/api_server.py` (선택적)

`get_logs()` 파라미터에 `session_id: str = ""` 추가, enrichment 후 필터링:
```python
if session_id:
    enriched = [e for e in enriched if session_id in e.get("session_id", "")]
```

---

## 작업 2 — 비회원 IP 수집

### 2-1. `integrated_PARK/logger.py`

`log_query()` 시그니처에 `client_ip: str = ""` 추가, record dict에 포함:
```python
def log_query(*, ..., user_id: str = "", client_ip: str = "", ...):
    record = { ..., "user_id": user_id, "client_ip": client_ip, ... }
```

`log_error()`에도 동일하게 `client_ip: str = ""` 추가.

### 2-2. `integrated_PARK/api_server.py`

IP 추출 헬퍼 함수 추가 (엔드포인트 정의 전):
```python
def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""
```

`/api/v1/query` 핸들러: `request: Request` 두 번째 파라미터 추가, `log_query()` 호출에 `client_ip=_get_client_ip(request)` 전달.

`/api/v1/stream` 핸들러: 동일하게 `request: Request` 추가 + `client_ip` 전달.

### 2-3. `frontend/src/components/LogTable.jsx`

EntryDetail 메타 영역에 IP 표시:
```jsx
{entry.client_ip && (
  <span className="text-muted-foreground font-mono" title="접속 IP">
    🌐 {entry.client_ip}
  </span>
)}
```

---

## 작업 3 — 개인정보처리방침 정비

**파일:** `frontend/src/pages/PrivacyPolicy.jsx`

### 삭제 항목
- 제2조 2.1: "공개 데이터를 AI 학습에 활용" → 삭제
- 제2조 2.2: "이용자 입력 데이터를 익명화 후 AI 학습 활용" → 삭제
- 제4조 4.1: "학습 데이터셋 생성 전 비식별화" → 삭제
- 제5조 "학습 활용 거부" 권리 → "데이터 삭제 요청"으로 대체

### 수정 항목
- 제2조 재구성: "서비스 제공 계약 이행"과 "정당한 이익(보안)"으로만 구성
- 제3조 수집 항목 테이블 교체:

| 구분 | 항목 | 보유 기간 |
|------|------|---------|
| 비회원 서비스 이용 | 대화 이력, 에이전트 요청 내역, 세션 ID | 24시간 |
| 로그인 회원 서비스 이용 | 대화 이력, 에이전트 요청 내역, 세션 ID, Google 계정명·이메일·식별자 | 30일 (탈퇴 요청 시 즉시 삭제) |
| 자동 수집 (전체) | 서비스 접속 로그, IP 주소 (보안·어뷰징 탐지 목적) | 6개월 |
| 수집 금지 | 주민등록번호, 계좌번호, 여권번호 등 고유식별정보 | 수집하지 않습니다 |

### 추가 항목
페이지 최하단에 시행일·버전 명시:
```jsx
<p className="text-xs text-muted-foreground text-center mt-4">
  시행일: 2026년 4월 7일 &nbsp;|&nbsp; 버전: 1.1
</p>
```

---

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `integrated_PARK/logger.py` | 작업 2 — client_ip 파라미터 |
| `integrated_PARK/api_server.py` | 작업 1(선택), 작업 2 — IP 헬퍼 + session_id 필터 |
| `frontend/src/pages/LogViewer.jsx` | 작업 1 — sessionFilter 상태 + 검색 UI |
| `frontend/src/components/LogTable.jsx` | 작업 1, 2 — session_id·IP 표시 |
| `frontend/src/pages/PrivacyPolicy.jsx` | 작업 3 — 조항 정비 |

---

## 검증 (통합 커밋·PR 생성 후)

### API 테스트
```bash
source integrated_PARK/.env

# IP 수집 확인
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트"}' > /dev/null

curl -s -H "X-API-Key: $API_KEY" "$BACKEND_HOST/api/v1/logs?limit=1" \
  | python3 -m json.tool | grep -E "client_ip|session_id"
```

### 프론트엔드 UI (Playwright)
1. LogViewer 접속 → 세션 ID 앞 8자 목록 표시 확인
2. EntryDetail에서 🔗 클릭 → 클립보드 복사 확인
3. 세션 ID 검색 input에 일부 입력 → 필터링 확인
4. 개인정보처리방침 페이지 → 수정된 조항 및 시행일 확인
