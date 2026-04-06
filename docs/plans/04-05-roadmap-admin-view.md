# 계획: 로드맵 진입 경로 추가 + 투표 집계 관리자 뷰

## Context
계층 3-D(로드맵 투표 위젯) 완료 후 두 가지 후속 작업:
1. `/roadmap` 페이지가 직접 URL 입력으로만 진입 가능 — 사용자가 기능을 발견하기 어려움
2. `/dev/logs` LogViewer에 투표 집계 데이터가 없어 개발자가 투표 현황을 확인할 수 없음

## 변경 파일

| 파일 | 작업 |
|------|------|
| `frontend/src/pages/Home.jsx` | footer에 `로드맵 투표` 링크 추가 |
| `frontend/src/pages/UserChat.jsx` | 헤더에 `로드맵 🗳️` 링크 추가 (내 리포트 옆) |
| `frontend/src/pages/MyReport.jsx` | main 하단에 로드맵 footer 링크 추가 |
| `frontend/src/pages/LogViewer.jsx` | "투표 집계" 탭 추가 |
| `frontend/src/api.js` | `fetchRoadmapVotes()` 함수 추가 (구현 전 파일 확인 필요) |

백엔드 변경 없음 — 기존 `GET /api/roadmap/votes` 엔드포인트 재사용.

---

## Task 1: /roadmap 진입 경로 추가

### 1a. Home.jsx — footer 링크 추가
```jsx
// 현재 (라인 ~100)
<Link to="/changelog" ...>업데이트 로그</Link>
<span className="mx-2 opacity-30">·</span>
<Link to="/privacy" ...>개인정보처리방침</Link>

// 변경 후 — 앞에 로드맵 추가
<Link to="/roadmap" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
  로드맵 투표
</Link>
<span className="mx-2 opacity-30">·</span>
<Link to="/changelog" ...>업데이트 로그</Link>
<span className="mx-2 opacity-30">·</span>
<Link to="/privacy" ...>개인정보처리방침</Link>
```

### 1b. UserChat.jsx — 헤더 링크 추가
헤더에서 `내 리포트 📊` 버튼 옆에 로드맵 링크 추가. 구현 전 헤더 정확한 위치 확인 필요.
```jsx
// 내 리포트 버튼 뒤에 추가
<a href="/roadmap" className="text-xs px-2 py-1 rounded ...">
  로드맵 🗳️
</a>
```

### 1c. MyReport.jsx — main 하단 footer 추가
`</main>` 닫기 직전에 footer 링크 섹션 추가:
```jsx
<p className="text-xs text-center" style={{ color: "var(--muted-foreground)" }}>
  <a href="/roadmap" style={{ color: "var(--brand-blue)" }}>
    🗳️ 다음에 추가할 기능 투표하기
  </a>
</p>
```

---

## Task 2: LogViewer 투표 집계 탭

### 2a. api.js — fetchRoadmapVotes 추가
`fetchLogs`, `fetchFeedback`와 동일한 패턴으로 추가:
```javascript
export async function fetchRoadmapVotes() {
  const res = await fetch(`${BASE_URL}/api/roadmap/votes`, { headers: _HEADERS });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json(); // { features: [{feature_id, label, icon, vote_count, user_voted}] }
}
```

### 2b. LogViewer.jsx — 탭 및 렌더링 추가

**TABS 배열:**
```javascript
const TABS = [
  { key: "queries", label: "전체 요청" },
  { key: "rejections", label: "거부 이력" },
  { key: "errors", label: "응답 오류" },
  { key: "roadmap", label: "투표 집계" },  // 추가
];
```

**상태 추가:**
```javascript
const [roadmapFeatures, setRoadmapFeatures] = useState([]);
```

**useEffect 수정 — roadmap 탭 분기:**
```javascript
useEffect(() => {
  if (tab === "roadmap") {
    setLoading(true);
    fetchRoadmapVotes()
      .then((data) => setRoadmapFeatures(data.features || []))
      .catch((e) => setError(e.message))
      .finally(() => { setLoading(false); setLastFetched(new Date().toLocaleTimeString("ko-KR")); });
  } else {
    load(tab);
  }
}, [tab]);
```

**main 컨텐츠 — roadmap 탭 렌더링:**
```jsx
{tab === "roadmap" ? (
  <div className="flex flex-col gap-3 pt-2">
    {roadmapFeatures.map((feat) => (
      <div key={feat.feature_id}
        className="flex items-center justify-between rounded-xl border px-4 py-3"
        style={{ background: "var(--card)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{feat.icon}</span>
          <span className="text-sm font-medium">{feat.label}</span>
        </div>
        <span className="text-sm font-semibold px-3 py-1 rounded-lg"
          style={{ background: "var(--muted)", color: "var(--foreground)" }}>
          ▲ {feat.vote_count}
        </span>
      </div>
    ))}
  </div>
) : isErrorTab ? (
  <ErrorTable ... />
) : (
  <LogTable ... />
)}
```

**통계 바 — roadmap 탭에서 숨김:**
```jsx
{total > 0 && tab !== "roadmap" && (
  <div className="glass border-b ...">
    {/* 기존 통계 */}
  </div>
)}
```

---

## 검증 (TC)

| TC | 내용 | 방법 |
|----|------|------|
| TC1 | `/home` 하단 footer에 "로드맵 투표" 링크 표시 | playwright `browser_navigate` + `browser_snapshot` |
| TC2 | `/user` 헤더에 "로드맵 🗳️" 링크 표시 | playwright snapshot |
| TC3 | `/my-report` 하단에 로드맵 링크 표시 | playwright snapshot |
| TC4 | 각 링크 클릭 시 `/roadmap`으로 이동 | playwright `browser_click` |
| TC5 | `/dev/logs` → "투표 집계" 탭 클릭 시 기능 목록 표시 | playwright snapshot |
| TC6 | 투표 집계 탭에서 vote_count 내림차순 표시 확인 | playwright snapshot |
