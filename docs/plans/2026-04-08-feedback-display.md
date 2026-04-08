# ReportSummary — feedback 데이터 시각화 추가

## Context

`ReportSummary.jsx`는 `feedback` prop을 받도록 설계되어 있으나 실제로는 렌더링에 사용하지 않았다.
서브 페이지 리디자인 과정에서 해당 prop이 dead code로 판단되어 제거되었으나,
`feedback.positive_rate` / `top_negative_tags` 등 응답 만족도 데이터를 실제로 표시하는 것이 기획 의도이므로 복원 + 표시 기능을 추가한다.

---

## feedback 데이터 구조

```js
feedback: {
  positive:          number,    // 긍정 피드백 수
  negative:          number,    // 부정 피드백 수
  total:             number,    // 전체 피드백 수
  positive_rate:     number,    // 0.0–1.0 (예: 0.75 → 75%)
  top_negative_tags: string[],  // 부정 사유 태그 (예: ["incorrect", "unclear"])
}
```

MyReport.jsx에서 `feedback={report.feedback}` 으로 전달 중 (현재는 ReportSummary에서 무시됨).

---

## 구현 방안

기존 3-stat grid (총 질문 수 / 주요 에이전트 / 체크리스트 진행률) 아래에
**독립 glass 카드 1개**를 추가한다. 이유:

- 3-stat grid의 시각적 균형을 유지 (4열로 늘리면 모바일에서 2×2 레이아웃 필요, 복잡도 증가)
- feedback에는 progress bar + 태그 badges 등 grid 카드보다 풍부한 내용이 포함됨
- `feedback.total === 0` 이면 섹션 자체를 숨김 → 깔끔한 빈 상태 처리

### 카드 내부 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  [ThumbsUp 아이콘 컨테이너]  응답 만족도              │
│                                                        │
│  75%  ████████████████░░░░  (긍정 75 / 부정 25)        │
│  progress bar: green(positive) | red(negative)         │
│                                                        │
│  부정 사유: [incorrect] [unclear]  ← 태그가 있을 때만  │
└──────────────────────────────────────────────────────┘
```

### 세부 명세

| 요소 | 구현 |
|------|------|
| 카드 래퍼 | `.glass .rounded-2xl .shadow-elevated` (기존 stat 카드와 동일 패턴) |
| 헤더 아이콘 | `ThumbsUp` (lucide-react), `w-8 h-8 rounded-xl`, `rgba(16,185,129,0.12)` 배경 |
| 만족도 수치 | `positive_rate * 100` 반올림, `font-bold text-2xl`, 색상 `#10b981` (75% 이상) / `#eab308` (50–74%) / `#ef4444` (50% 미만) |
| progress bar | `h-2.5 rounded-full` 컨테이너, 내부 두 segment(green + red) 를 `flex` 비율로 표현 |
| 건수 breakdown | `긍정 N건 · 부정 N건` — `text-xs muted-foreground` |
| top_negative_tags | `slice(0, 3)`, `text-xs px-2.5 py-1 rounded-full`, `rgba(239,68,68,0.12)` 배경 + `#ef4444` 텍스트 |
| 피드백 없음 | `feedback?.total === 0 \|\| !feedback` → 카드 미렌더링 |
| 애니메이션 | `motion.div whileInView`, `opacity: 0→1`, `y: 20→0`, `delay: 0.35` (stat 카드 이후) |

---

## 변경 파일

- `frontend/src/components/report/ReportSummary.jsx` — feedback 섹션 카드 추가

MyReport.jsx는 이미 `feedback={report.feedback}`를 전달 중이므로 수정 불필요.

---

## 검증

```bash
cd frontend && npm run dev
```

1. `/report` 접속 — 피드백 데이터 있는 세션에서 만족도 수치, progress bar 비율, 부정 태그 badges 노출 확인
2. `feedback.total === 0` 또는 `feedback` 없을 때 카드 미노출 확인
3. 다크모드 전환 후 progress bar / badge 색상 깨짐 없는지 확인
4. `npm run build` 에러 없이 성공 확인
