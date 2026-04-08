# 세션 인수인계 — 2026-04-08 (Phase B·CD 완료)

## 완료된 작업

### Phase E-backend (PR #216, MERGED)
- GZipMiddleware, DB 인메모리 캐싱(5분 TTL), X-Response-Time-MS 헤더

### Phase A-bundle (PR #224, MERGED)
- React.lazy() 11개 페이지, manualChunks 6개 vendor 청크

### Phase B-network (PR #227, MERGED)
**브랜치**: `PARK-perf-B-network`

수정 파일:
- `frontend/src/api.js`
  - `fetchWithTimeout(url, options, ms=15000)` 유틸 추가
  - REST 5개 함수(`sendQuery`, `fetchLogs`, `fetchLogUsers`, `fetchRoadmapVotes`, `fetchFeedback`)에 적용
  - 에러 파싱 개선: `res.text()` + `JSON.parse` + `err.message` 폴백

이미 이전 세션에서 구현됨 (PR #227에 포함되지 않음):
- B1: `streamQuery` AbortController (`frontend/src/api.js` + `useStreamQuery.js`)
- B3: activeEvents 정리

### Phase CD-api-ux (PR #228, MERGED)
**브랜치**: `PARK-perf-CD-api-ux`

수정 파일:
- `frontend/src/hooks/map/useDongCache.js` — 5분 TTL + `clearByQtr()` 분기별 부분 무효화
- `frontend/src/pages/LogViewer.jsx` — `feedbackCacheRef`로 탭 전환 중복 요청 제거
- `frontend/src/pages/MyLogs.jsx` — 로딩 스피너, SessionCard 에러/빈 목록 구분
- `frontend/src/pages/Roadmap.jsx` — 투표 실패 시 `sonner` toast 알림
- `frontend/src/hooks/chat/useStreamQuery.js` — `onMessage`·`onUpdateAt`·`onParams` useRef stale closure 수정, `submit`·`regenerate` 의존성 배열 단순화
- `frontend/src/components/map/MapView.jsx` — `storesByAdmCdRef` per-admCd 상가 캐시 추가

스킵:
- C4(useChecklistState 디바운싱): `frontend/src/hooks/chat/useChecklistState.js` 파일 미존재

---

## 전체 플랜 현황

**플랜 파일**: `~/.claude/plans/dynamic-kindling-wombat.md`

| Phase | 브랜치 | 상태 | 내용 |
|-------|--------|------|------|
| E-backend | `PARK-perf-E-backend-v2` | ✅ MERGED (#216) | GZip·DB캐시·응답시간 헤더 |
| A-bundle  | `PARK-perf-A-bundle`    | ✅ MERGED (#224) | React.lazy·manualChunks |
| B-network | `PARK-perf-B-network`   | ✅ MERGED (#227) | fetch 타임아웃·에러 파싱 |
| CD-api-ux | `PARK-perf-CD-api-ux`   | ✅ MERGED (#228) | 중복 제거·UX 개선 |
| E-deep    | `PARK-perf-E-deep`      | ⏳ **미시작** | 에이전트 타임아웃·Monte Carlo 비동기화·세션 스토어 |

---

## 다음 세션 — Phase E-deep

**브랜치명**: `PARK-perf-E-deep`

```bash
git fetch origin
git checkout -b PARK-perf-E-deep origin/main
```

### E3. 에이전트별 LLM 타임아웃 분화

**현황**: 모든 에이전트에서 `asyncio.wait_for(..., timeout=60.0)` 동일 적용.

확인된 파일 및 라인:
- `integrated_PARK/agents/admin_agent.py`: 라인 120, 124
- `integrated_PARK/agents/chat_agent.py`: 라인 154 (`timeout=30.0` — 이미 다름, 유지)
- `integrated_PARK/agents/finance_agent.py`: 라인 136/138, 212/214, 224/226
- `integrated_PARK/agents/legal_agent.py`: 라인 127, 131
- `integrated_PARK/agents/location_agent.py`: 라인 273/275, 289/294

**변경 방법**: `integrated_PARK/agents/` 최상단 어느 에이전트 파일 또는 별도 `_timeouts.py`에 상수 정의:

```python
# integrated_PARK/agents/_timeouts.py (신규 파일)
AGENT_TIMEOUTS = {
    "admin":    45.0,
    "finance":  20.0,
    "legal":    50.0,
    "location": 55.0,
    "chat":     30.0,   # 이미 30.0으로 설정됨
    "signoff":  30.0,
}
```

각 에이전트에서 `from ._timeouts import AGENT_TIMEOUTS` 후 `timeout=AGENT_TIMEOUTS["finance"]` 교체.

### E4. Monte Carlo 시뮬레이션 비동기화

**현황**: `integrated_PARK/plugins/finance_simulation_plugin.py`의 `monte_carlo_simulation()` 함수가 동기(sync) — 10,000회 루프로 2-3초 블로킹.

호출 위치: `integrated_PARK/agents/finance_agent.py` 라인 278
```python
sim_result = self._sim.monte_carlo_simulation(**sim_input)  # 동기 호출
```

**변경 방법**:
1. `finance_simulation_plugin.py`에 async 래퍼 추가:
```python
import asyncio
import concurrent.futures

class FinanceSimulationPlugin:
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def monte_carlo_simulation_async(self, **kwargs) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.monte_carlo_simulation(**kwargs)
        )
```

2. `finance_agent.py` 라인 278 교체:
```python
sim_result = await self._sim.monte_carlo_simulation_async(**sim_input)
```

3. `investment_recovery`와 `breakeven_analysis_mc`는 빠른 연산이므로 동기 유지.

### E5. 세션 스토어 LRU 교체

> ⚠️ **주의**: `session_store.py`는 Cosmos DB 백엔드를 사용하며, TTL은 Cosmos DB 자체 TTL(`COSMOS_SESSION_TTL`)로 관리됨 (기본 86400초). **인메모리 폴백(`_memory_store` dict)에만 LRU가 필요**.

**현황 확인 필요**: `_evict_if_needed()` 함수(라인 104)가 FIFO인지 확인 후 LRU로 교체 여부 결정.
- Cosmos DB 모드에서는 E5 건너뛰어도 무방
- 인메모리 폴백 사용 중이면 `collections.OrderedDict` 기반 LRU 적용 검토

---

## 주의사항

- **`GlowCTA.jsx`**: `frontend/src/components/GlowCTA.jsx` — shimmer+orb 패턴 공통 컴포넌트, Landing·Features·PrivacyPolicy 사용 중. 중복 shimmer 구현 금지
- **리디자인 완료 페이지**: Landing, Features, PrivacyPolicy, Roadmap, MyReport, MyLogs — glass/gradient 스타일 유지
- **E-deep는 백엔드 전용**: 프론트엔드 변경 없음, `npm run build` 불필요
- **배포 확인**: `.venv/bin/python3 -c "import api_server"` import 검증 후 PR 생성
- **브랜치 슬래시 불가**: `PARK-perf-E-deep` 대시 형식
