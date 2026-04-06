# 플랜: 랜딩 페이지 AI 전문가 섹션 업데이트

## Context
현재 랜딩 페이지의 "세 명의 AI 전문가" 섹션은 실제 백엔드 에이전트 구조와 맞지 않습니다.

- 실제 에이전트: **4개** (admin, legal, finance, commercial)
  - `admin_agent.py` ↔ `legal_agent.py`가 분리되어 있으나 UI에서는 하나로 합쳐져 있음
- `mockData.js`의 플러그인 목록이 전부 영어
- SignOff 카드 설명이 기술적이어서 일반 사용자가 이해하기 어려움

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/data/mockData.js` | agentData 3→4개 에이전트, 플러그인 목록 제거, 한국어 설명 업데이트 |
| `frontend/src/components/AgentCard.jsx` | 플러그인 목록 렌더링 제거, 카드 레이아웃 정리 |
| `frontend/src/pages/Landing.jsx` | 섹션 제목·그리드 레이아웃·SignOff 설명 업데이트 |

---

## Step 1 — `mockData.js` 에이전트 데이터 교체

`agentData` 배열을 4개로 교체. `plugins` 필드 제거, 한국어 `features` 배열(2–3개 핵심 기능) 추가.

```js
export const agentData = [
  {
    id: 'admin',
    nameKo: '행정 에이전트',
    descriptionKo: '영업신고·위생교육·사업자등록·보건증·소방 절차와 정부지원사업 맞춤 추천',
    icon: 'FileText',
    color: '#0891b2',
    features: ['영업신고 & 인허가 절차', '정부지원금 맞춤 추천', '법령 근거 단계별 안내'],
  },
  {
    id: 'legal',
    nameKo: '법무 에이전트',
    descriptionKo: '임대차 계약, 권리금, 상가건물임대차보호법 등 법률 정보 안내',
    icon: 'Scale',
    color: '#6366f1',
    features: ['임대차·권리금 계약 검토', '상가임대차보호법 안내', '법적 분쟁 대응 정보'],
  },
  {
    id: 'finance',
    nameKo: '재무 에이전트',
    descriptionKo: '몬테카를로 시뮬레이션으로 월 순이익 분포·손익분기·투자 회수 기간 분석',
    icon: 'Calculator',
    color: '#f97316',
    features: ['10,000회 수익 시뮬레이션', '손익분기점 & 안전마진', '투자 회수 기간 예측'],
  },
  {
    id: 'commercial',
    nameKo: '상권분석 에이전트',
    descriptionKo: '서울 상권 DB(2024년 4분기) 기반 매출·유동인구·경쟁업체 분석 및 입지 비교',
    icon: 'MapPin',
    color: '#14b8a6',
    features: ['월매출·점포수 데이터 조회', '시간대별 유동인구 분석', '유사 상권 추천 & 비교'],
  },
];
```

---

## Step 2 — `AgentCard.jsx` 플러그인 목록 제거

- `agent.plugins` 렌더링 블록(첫 4개 + "+N more") 전체 제거
- `agent.features` 배열(2–3개)을 간단한 체크 아이콘(`✓`) 리스트로 교체
- 아이콘 맵에 `Scale` 추가 (lucide-react에서 import)

---

## Step 3 — `Landing.jsx` 업데이트

### 3-1. 섹션 제목
`세 명의 AI 전문가` → `네 명의 AI 전문가`

### 3-2. 그리드 레이아웃
```jsx
// Before
<div className="grid md:grid-cols-3 gap-8">

// After (모바일 1열 → 태블릿 2열 → 데스크톱 4열)
<div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-6">
```

### 3-3. SignOff 카드 설명
```
Before: "모든 답변은 자동 품질 검증 파이프라인을 거쳐 신뢰성을 보장합니다"

After: "AI가 생성한 답변을 별도의 검증 AI가 한 번 더 검토해, 오류나 부정확한 정보를 사전에 걸러냅니다"
```

---

## 검증

```bash
cd frontend && npm run dev
```

브라우저에서 확인:
1. 랜딩 페이지 에이전트 섹션에 카드 4개 표시
2. 플러그인 목록 없이 한국어 기능 3줄씩 표시
3. SignOff 카드 설명이 평문으로 읽힘
4. 모바일(375px)·태블릿(768px)·데스크톱(1280px) 레이아웃 확인
