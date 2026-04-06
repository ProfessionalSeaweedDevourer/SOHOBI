# PR #61 → 최신 프론트엔드 통합 계획

## Context

PR #61 (CHANG 브랜치)은 재무 시뮬레이션 차트를 백엔드 matplotlib PNG → 프론트엔드 chart.js 동적 렌더링으로 전환한다.
그러나 main 브랜치는 PR #61 이후 두 개의 대규모 커밋이 추가되어 분기됐다:
- PR#56 지도-상권 연동 통합 (6c8ed4d)
- NeoFrontend 디자인 시스템 마이그레이션 54개 파일 (fe7717b) — glassmorphism, Tailwind v4, motion v12

이 상태에서 PR #61을 자동 머지하면 NeoFrontend 스타일 코드를 덮어쓰고, SimulationChart.jsx가 디자인 시스템을 따르지 않는다. 수동 체리픽 + 스타일 적응이 필요하다.

---

## 변경 파일 목록

### 백엔드 (그대로 적용 — 충돌 없음)
| 파일 | 내용 |
|------|------|
| `integrated_PARK/db/finance_db.py` | 신규 파일 — Oracle DB 연동 DBWork 클래스 |
| `integrated_PARK/plugins/finance_simulation_plugin.py` | 차트 반환 형식 변경 (Base64 PNG → JSON bins), 업종별 INDUSTRY_RATIO 추가, DB 연동 재개 |
| `integrated_PARK/agents/finance_agent.py` | 공백 한 줄 — 무시 가능 |
| `integrated_PARK/kernel_setup.py` | 개행 정리 — 무시 가능 |

### 프론트엔드 (수동 적용 — 스타일 조정 필요)
| 파일 | 내용 |
|------|------|
| `frontend/package.json` | `chart.js ^4.5.1` 의존성 추가 |
| `frontend/package-lock.json` | lock 파일 갱신 (npm install로 자동 처리) |
| `frontend/src/components/SimulationChart.jsx` | 신규 파일 — glassmorphism 스타일로 재작성 필요 |
| `frontend/src/components/ResponseCard.jsx` | chart 렌더링 블록 교체 (img → SimulationChart) |
| `frontend/src/pages/UserChat.jsx` | 변경 불필요 (현재 `chart: finalResult.chart` 그대로 사용) |

---

## 충돌 분석

| 파일 | 충돌 유형 | 처리 방법 |
|------|---------|---------|
| `ResponseCard.jsx` | 현재 NeoFrontend glass 스타일. PR#61 패치가 구버전 기준. | 수동 적용 — 71-79행 `<img>` 블록만 `<SimulationChart chartData={chart} />`로 교체 |
| `UserChat.jsx` | PR#61은 `chartData` prop 추가 시도. 현재 코드는 `chart` 사용. | 변경 없이 유지 — prop 이름 `chart`로 통일 |
| `SimulationChart.jsx` | 신규 파일. PR#61 버전은 plain JS 스타일. | glassmorphism + CSS variables로 재작성 |
| `finance_simulation_plugin.py` | 가장 큰 변경 (116줄 추가, 77줄 삭제). main에서는 수정 없음. | 그대로 적용 |

---

## 구현 단계

### 1. 백엔드 변경 적용
```bash
git checkout CHANG -- integrated_PARK/db/finance_db.py
git checkout CHANG -- integrated_PARK/plugins/finance_simulation_plugin.py
```
- `finance_db.py`: Oracle DSN은 `.env`의 기존 설정 사용 (커밋하지 말 것)
- `finance_simulation_plugin.py`: INDUSTRY_RATIO dict + `_generate_chart()` JSON bins 반환 로직

### 2. chart.js 의존성 추가
```bash
cd frontend && npm install chart.js@^4.5.1
```
package-lock.json은 npm install로 자동 갱신.

### 3. SimulationChart.jsx 신규 작성 (glassmorphism 스타일)

`frontend/src/components/SimulationChart.jsx`

- chart.js `Bar` 차트 (PR #61 로직 유지)
- 색상: `var(--brand-teal)` (손실), `var(--brand-blue)` (수익), 노란계열 (P20 경계)
- 컨테이너: `glass rounded-2xl p-4` (NeoFrontend 클래스)
- chart.js 인스턴스 cleanup: useEffect return에서 `chartRef.current.destroy()`
- 반응형: `responsive: true`

### 4. ResponseCard.jsx 수정

`frontend/src/components/ResponseCard.jsx:71-79` — 기존 `<img>` 블록 교체:

```jsx
// 변경 전 (71-79행)
{chart && (
  <div className="mt-3">
    <img src={`data:image/png;base64,${chart}`} alt="..." className="rounded-lg max-w-full" />
  </div>
)}

// 변경 후
{chart && typeof chart === "object" && (
  <div className="mt-3">
    <SimulationChart chartData={chart} />
  </div>
)}
```

- 상단에 `import SimulationChart from "./SimulationChart";` 추가
- `typeof chart === "object"` 가드: 구버전 Base64 문자열 응답이 들어와도 렌더링 오류 방지

### 5. UserChat.jsx — 변경 없음

현재 코드(58행, 124행)가 이미 `chart` prop으로 올바르게 연결됨. PR #61의 `chartData` 이름 변경은 채택하지 않는다.

---

## 검증 방법

1. `cd frontend && npm install` 후 `npm run dev` — 빌드 에러 없음 확인
2. 백엔드 실행: `cd integrated_PARK && .venv/bin/python3 api_server.py`
3. 재무 질문 전송:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"question": "월매출 700만원, 재료비 200만원으로 분식집 창업 시 수익성은?"}'
   ```
4. 응답의 `chart` 필드가 `{"bins": [...], "avg": ..., "p20": ..., "min": ..., "max": ...}` JSON 형식인지 확인
5. 브라우저에서 `/user` 페이지 — 재무 질문 입력 후 히스토그램 chart.js 차트가 glassmorphism 카드 안에 렌더링되는지 확인
6. 다크모드 토글 후 차트 색상(CSS variables) 정상 표시 확인

---

## 핵심 파일 경로

- [ResponseCard.jsx](frontend/src/components/ResponseCard.jsx) — 71-79행 수정
- [SimulationChart.jsx](frontend/src/components/SimulationChart.jsx) — 신규 작성
- [UserChat.jsx](frontend/src/pages/UserChat.jsx) — 변경 없음
- [finance_simulation_plugin.py](integrated_PARK/plugins/finance_simulation_plugin.py) — 전체 교체
- [finance_db.py](integrated_PARK/db/finance_db.py) — 신규 추가
- [package.json](frontend/package.json) — chart.js 추가
