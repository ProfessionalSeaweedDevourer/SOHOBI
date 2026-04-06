# 로그 뷰어 — 전체 다운로드 버튼 추가

## Context

현재 로그 뷰어는 최근 100개만 표시한다. 전량을 항상 테이블에 표시하면 DOM 성능 문제가 생길 수 있으므로,
테이블 표시는 합리적인 한도(500개)로 올리고, 별도 "전체 다운로드" 버튼으로 전량을 JSON 파일로 저장하는 방식을 채택한다.

Azure Container Apps 직접 접근 대신 이 버튼을 사용하는 이유:
- Container Apps 로그 스트림은 stdout/stderr만 노출 (구조화된 JSONL 아님)
- Blob Storage 직접 접근은 Azure Portal에서 별도 탐색 필요
- 버튼 하나로 현재 필터(type) 기준 전량을 바로 저장 가능

---

## 수정 내용

### 파일 1: `frontend/src/api.js`

```javascript
// 변경 전 (line 92)
export async function fetchLogs(type = "queries", limit = 50) {

// 변경 후
export async function fetchLogs(type = "queries", limit = 500) {
```

기본값을 500으로 올림. 0이면 백엔드가 전량 반환.

---

### 파일 2: `frontend/src/pages/LogViewer.jsx`

1. `fetchLogs(type, 100)` → `fetchLogs(type)` (기본값 500 사용)
2. 다운로드 버튼 추가:

```jsx
// 다운로드 핸들러 추가
const handleDownload = async () => {
  setDownloading(true);
  try {
    const data = await fetchLogs(activeTab, 0); // 0 = 전량
    const blob = new Blob(
      [JSON.stringify(data.entries, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sohobi-logs-${activeTab}-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } finally {
    setDownloading(false);
  }
};

// useState 추가
const [downloading, setDownloading] = useState(false);

// 버튼 JSX — 탭 옆이나 상단 우측에 배치
<button
  onClick={handleDownload}
  disabled={downloading}
  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded border"
>
  {downloading ? "다운로드 중..." : "전체 다운로드 (JSON)"}
</button>
```

---

## 수정 대상 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/api.js` | `fetchLogs` 기본 limit 50 → 500 |
| `frontend/src/pages/LogViewer.jsx` | limit 100 → 기본값, 다운로드 버튼 추가 |

---

## 보안 조치 이후 작업 PC 접근 (참고)

`docs/plans/2026-03-30-backend-security-plan.md` Phase 1 적용 후, 프론트엔드 로그 뷰어는 SWA 프록시 + VITE_API_KEY를 통해 그대로 동작.
작업 PC에서 직접 curl로 프로덕션 로그를 조회하려면:

```bash
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=0" \
  -H "X-API-Key: $API_SECRET_KEY" > logs_all.json
```

IP 화이트리스트(Phase 2) 활성화 시 작업 PC IP를 `ALLOWED_IPS`에 추가해야 한다.

---

## 검증

1. 로컬 백엔드 기동 후 로그 뷰어에서 500개까지 로드되는지 확인
2. 다운로드 버튼 클릭 → JSON 파일 저장, 엔트리 수가 500개 초과인지 확인 (로그가 충분한 경우)
