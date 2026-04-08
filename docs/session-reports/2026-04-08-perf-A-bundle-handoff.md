# 세션 인수인계 — 2026-04-08 (Phase A-bundle 완료)

## 완료된 작업

### Phase E-backend (PR #215 → #216, MERGED)
- GZipMiddleware, DB 인메모리 캐싱(5분 TTL), X-Response-Time-MS 헤더
- PR #216: 코드 리뷰 반영 (lazy eviction, 캐시 키 구분자 개선)

### 디자인 리팩터링 (PR #219, #221, MERGED)
- PR #219: Roadmap·MyReport·MyLogs·ReportSummary·AgentUsageChart·Recommendations 전면 리디자인
- PR #221: AnimatePresence key 버그 수정 + GlowCTA 공통 컴포넌트 추출 (Landing, Features, PrivacyPolicy 적용)

### Phase A-bundle (PR #224, MERGED)
**브랜치**: `PARK-perf-A-bundle`

수정 파일:
- `frontend/src/App.jsx` — 11개 페이지 `React.lazy()` 전환, `<Suspense fallback={<LoadingSpinner />}>` 래핑
- `frontend/vite.config.js` — `manualChunks` 6개 vendor 청크 분리

정적 유지 (초기 로드 필수): Landing, Home, UserChat

번들 결과:
| 청크 | 크기 |
|------|------|
| `index-*.js` | **508KB** (이전 ~1.4MB, -64%) |
| `vendor-map-*.js` (ol+turf) | 284KB |
| `vendor-markdown-*.js` | 156KB |
| `vendor-motion-*.js` | 95KB |

---

## 전체 플랜 현황

**플랜 파일**: `~/.claude/plans/optimized-cooking-reddy.md`

| Phase | 브랜치 | 상태 | 내용 |
|-------|--------|------|------|
| E-backend | `PARK-perf-E-backend-v2` | ✅ MERGED (#216) | GZip·DB캐시·응답시간 헤더 |
| A-bundle  | `PARK-perf-A-bundle`    | ✅ MERGED (#224) | React.lazy·manualChunks |
| B-network | `PARK-perf-B-network`   | ⏳ 미시작 | SSE AbortController·타임아웃 |
| CD-api-ux | `PARK-perf-CD-api-ux`   | ⏳ 미시작 | 중복 요청 제거·UX 보완 |
| E-deep    | `PARK-perf-E-deep`      | ⏳ 미시작 | 에이전트 타임아웃·Monte Carlo 비동기화 |

---

## 다음 세션 — Phase B-network

**브랜치명**: `PARK-perf-B-network`

```bash
git fetch origin
git checkout -b PARK-perf-B-network origin/main
```

### B1. SSE AbortController (`frontend/src/api.js`, `frontend/src/hooks/chat/useStreamQuery.js`)

`api.js`의 `streamQuery` 함수에 `signal` 파라미터 추가:
```js
export async function streamQuery(..., signal = null) {
  const res = await fetch(url, { method: "POST", headers, body, signal });
  const reader = res.body.getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done || signal?.aborted) break;
      // 파싱 로직 유지
    }
  } finally {
    reader.cancel();
  }
}
```

`useStreamQuery.js`에 AbortController 훅 추가:
```js
const controllerRef = useRef(null);
const _runStream = useCallback(async (...) => {
  controllerRef.current?.abort();
  controllerRef.current = new AbortController();
  await streamQuery(..., controllerRef.current.signal);
}, [...]);
useEffect(() => () => controllerRef.current?.abort(), []);
```

### B2. fetch 타임아웃 유틸리티 (`frontend/src/api.js` 상단)

```js
function fetchWithTimeout(url, options = {}, ms = 15000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { ...options, signal: ctrl.signal }).finally(() => clearTimeout(id));
}
```

SSE는 B1 AbortController로 처리, REST 호출에만 적용

### B3. activeEvents 메모리 누수 (`frontend/src/hooks/chat/useStreamQuery.js`)

`complete` 또는 `error` 이벤트 수신 후 `setActiveEvents([])` 호출

### B4. 에러 응답 파싱 개선 (`frontend/src/api.js`)

```js
const text = await res.text();
let err = {};
try { err = JSON.parse(text); } catch {}
throw new Error(err.error || err.message || `HTTP ${res.status}`);
```

---

## 주의사항

- **`GlowCTA.jsx`** (PR #221 신규): `frontend/src/components/GlowCTA.jsx` — shimmer+orb 패턴 공통 컴포넌트, Landing·Features·PrivacyPolicy 사용 중. B~CD 작업 시 중복 shimmer 구현 금지
- **리디자인 완료 페이지**: Landing, Features, PrivacyPolicy, Roadmap, MyReport, MyLogs — JSX 내용 수정 시 glass/gradient 스타일 유지
- **브랜치 슬래시 불가**: `PARK-xxx` 대시 형식만 사용
- **`PARK-dev-summary-restructure`**: 별도 작업 브랜치, 건드리지 말 것
