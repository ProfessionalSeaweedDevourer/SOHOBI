# 로그 뷰어 에이전트 색상 중복 수정

## Context

프론트엔드 로그 뷰어에서 `location`(상권분석) 에이전트와 `chat`(안내) 에이전트가 동일한 보라색(`#8b5cf6`)을 사용하고 있어 시각적으로 구분이 불가능하다. 하드코딩된 색상 맵에서 두 키가 같은 값을 가리키도록 작성된 것이 원인.

추가로 `ResponseCard.jsx`에서는 `location`이 `finance`와 동일한 teal 색상을 사용하고 있어 그쪽도 충돌이 있다.

## 확정 색상 팔레트

| 도메인 | 한국어 | 색상 | 비고 |
|--------|--------|------|------|
| finance | 재무 | teal (#10b981 / --brand-teal) | 기존 유지 |
| admin | 행정 | blue (--brand-blue) | 기존 유지 |
| legal | 법무 | amber/orange | 기존 유지 |
| **location** | **상권분석** | **violet `#8b5cf6`** | 기존 LogTable 색상 유지 |
| **chat** | **안내** | **pink `#ec4899`** | 새로 배정 (rose-500) |

## 수정 파일 및 변경 내용

### 1. [frontend/src/components/LogTable.jsx](frontend/src/components/LogTable.jsx) — 줄 11

```diff
- chat: { background: "rgba(139,92,246,0.12)", color: "#8b5cf6" },
+ chat: { background: "rgba(236,72,153,0.12)", color: "#ec4899" },
```

### 2. [frontend/src/components/ResponseCard.jsx](frontend/src/components/ResponseCard.jsx) — 줄 9-10

```diff
- location:{ background: "rgba(20,184,166,0.15)", color: "var(--brand-teal)" },
- chat:    { background: "rgba(139,92,246,0.15)", color: "#8b5cf6" },
+ location:{ background: "rgba(139,92,246,0.15)", color: "#8b5cf6" },
+ chat:    { background: "rgba(236,72,153,0.15)", color: "#ec4899" },
```

## 검증

1. `cd frontend && npm run dev` 로 개발 서버 실행
2. 로그 뷰어 페이지 열기
3. 상권분석(location) 항목 → 보라색 뱃지 확인
4. 안내(chat) 항목 → 분홍색 뱃지 확인 (이전과 다른 색)
5. ResponseCard 에서도 동일하게 두 에이전트가 구분되는지 확인
