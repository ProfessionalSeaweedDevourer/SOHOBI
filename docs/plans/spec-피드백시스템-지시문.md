# SOHOBI 사용자 피드백 시스템 — Claude Code 개발 지시문

> **목적**: SOHOBI 서비스 내부에 사용자 피드백 수집 시스템을 구현한다.
> **범위**: 인라인 피드백 위젯(계층 2) + 사용 추적 및 리포트(계층 3)
> **마감**: 계층 2는 즉시 구현, 계층 3은 출시 후 1~2주 내 구현
> **기술 스택**: React (프론트엔드), FastAPI (백엔드), Azure Cosmos DB (세션/데이터 저장), Azure Blob Storage (로그)
> **저장소**: `ProfessionalSeaweedDevourer/SOHOBI`

---

## 사전 작업: 코드베이스 파악

구현을 시작하기 전에 반드시 아래 항목을 확인하라.

1. **에이전트 응답 렌더링 컴포넌트**를 찾는다.
   - `ChatMessage`, `AgentResponse`, `MessageBubble` 등의 이름일 수 있다.
   - 이 컴포넌트가 인라인 피드백 위젯의 삽입 지점이다.

2. **세션 관리 방식**을 파악한다.
   - 현재 세션 ID를 어디서 가져오는지 (Context, Redux, zustand, 또는 props 체인)
   - 에이전트 유형(agent_type)이 응답 데이터에 어떤 키로 포함되어 있는지
   - 개별 메시지의 고유 ID(message_id)가 존재하는지, 없다면 생성 방식

3. **기존 HTTP 클라이언트**를 확인한다.
   - axios 인스턴스, fetch wrapper, 또는 별도의 API 유틸이 있는지
   - base URL 설정 방식, 인증 헤더 처리 방식

4. **기존 Cosmos DB 클라이언트 코드**를 확인한다.
   - 백엔드에서 Cosmos DB에 문서를 생성하는 기존 패턴 (azure-cosmos SDK 사용법, 데이터베이스/컨테이너 참조 방식)

5. **기존 디자인 토큰**을 확인한다.
   - 색상 변수, 폰트, 간격, 버튼 스타일 등이 정의된 파일 (CSS 변수, styled-components 테마, tailwind config 등)

> 위 항목을 파악한 후, 이 문서의 명세에서 실제 코드베이스와 맞지 않는 부분(컴포넌트명, import 경로, 상태 관리 방식 등)을 코드베이스에 맞게 조정하여 구현하라.

---

## 계층 2: 인라인 피드백 위젯

### 개요

각 에이전트의 응답이 완료된 후, 응답 하단에 간단한 피드백 수집 UI를 표시한다.
서비스 사용 중 맥락에서 수집하므로, 외부 설문보다 응답률이 높고 데이터의 맥락 품질이 좋다.

### UI 와이어프레임

```
┌──────────────────────────────────────────────┐
│  [에이전트 응답 내용]                          │
│                                              │
│  ─────────────────────────────────────────── │
│  이 답변이 도움이 되었나요?   👍  👎          │
│                                              │
│  [👎 클릭 시에만 펼쳐지는 영역]                │
│  어떤 점이 부족했나요? (복수 선택 가능)         │
│  ┌──────────┐ ┌──────────────┐               │
│  │ 정확하지  │ │ 이해하기     │               │
│  │ 않음     │ │ 어려움       │               │
│  └──────────┘ └──────────────┘               │
│  ┌──────────────┐ ┌──────────┐               │
│  │ 내 상황에     │ │ 정보가   │               │
│  │ 맞지 않음    │ │ 부족함   │               │
│  └──────────────┘ └──────────┘               │
│                        [제출]                 │
│                                              │
│  [제출 후] "의견 감사합니다!" (1.5초 후 축소)   │
└──────────────────────────────────────────────┘
```

### 파일 구조

```
src/
  components/
    feedback/
      InlineFeedback.jsx       ← 메인 컴포넌트 (👍/👎 + 전체 흐름 관리)
      FeedbackTags.jsx         ← 👎 선택 시 나타나는 태그 선택 영역
      useFeedbackSubmit.js     ← 피드백 전송 커스텀 훅
      feedbackConstants.js     ← 태그 목록, 문구 등 상수
```

> 기존 프로젝트의 폴더 구조 컨벤션에 따라 경로를 조정하라. 예를 들어 `components/common/`, `components/chat/` 등의 패턴이 있다면 그에 맞추라.

### 상수 정의: `feedbackConstants.js`

```javascript
export const NEGATIVE_FEEDBACK_TAGS = [
  { id: 'inaccurate',        label: '정확하지 않음' },
  { id: 'hard_to_understand', label: '이해하기 어려움' },
  { id: 'not_relevant',      label: '내 상황에 맞지 않음' },
  { id: 'insufficient',      label: '정보가 부족함' },
];

export const FEEDBACK_MESSAGES = {
  prompt: '이 답변이 도움이 되었나요?',
  tagPrompt: '어떤 점이 부족했나요?',
  submitButton: '제출',
  thankYou: '의견 감사합니다!',
};

// A/B 테스트나 문구 변경 시 이 파일만 수정하면 된다.
```

### 컴포넌트 명세: `InlineFeedback.jsx`

**Props:**
| Prop | 타입 | 필수 | 설명 |
|---|---|---|---|
| sessionId | string | 예 | 현재 세션 ID (Cosmos DB 세션 키) |
| agentType | string | 예 | `"admin"` `"commercial"` `"financial"` `"legal"` `"validator"` 중 하나 |
| messageId | string | 예 | 해당 응답의 고유 ID |
| conversationContext | string | 아니오 | 사용자 질문 원문 또는 요약 (분석용으로 함께 저장) |

**상태 머신:**
```
idle ──[👍 클릭]──→ submitting ──→ complete
  │
  └──[👎 클릭]──→ tagging ──[제출 클릭]──→ submitting ──→ complete
```

- `idle`: 👍 👎 버튼만 표시
- `tagging`: 태그 선택 영역 펼침, 최소 1개 태그 선택 전까지 [제출] 비활성화
- `submitting`: API 호출 중, 버튼 비활성화 + 로딩 표시
- `complete`: "의견 감사합니다!" 표시, 1.5초 후 전체 영역을 단일 줄 "✓ 피드백 완료"로 축소

**핵심 동작 규칙:**
1. 한 번 피드백을 제출하면 같은 messageId에 대해 재제출 불가 (컴포넌트 상태로 관리)
2. 👍 클릭 시 태그 선택 없이 즉시 전송
3. 👎 클릭 시 태그 선택 영역 펼침 — 태그 1개 이상 선택 + [제출] 클릭으로 전송
4. 피드백 전송 실패 시 사용자에게 에러를 표시하지 않음 — console.warn으로 로그만 남기고, "의견 감사합니다!"를 그대로 표시 (피드백 수집 실패가 사용자 경험을 방해해서는 안 됨)

### 컴포넌트 명세: `FeedbackTags.jsx`

**Props:**
| Prop | 타입 | 필수 | 설명 |
|---|---|---|---|
| selectedTags | string[] | 예 | 현재 선택된 태그 ID 배열 |
| onTagToggle | (tagId: string) => void | 예 | 태그 클릭/해제 시 호출 |
| onSubmit | () => void | 예 | 제출 버튼 클릭 시 호출 |
| isSubmitDisabled | boolean | 예 | 태그 미선택 시 true |

**렌더링:**
- `NEGATIVE_FEEDBACK_TAGS`를 순회하며 칩(chip) 형태의 토글 버튼 렌더링
- 선택된 태그는 배경색 변경으로 시각적 구분
- 하단에 [제출] 버튼 배치

### 커스텀 훅: `useFeedbackSubmit.js`

```javascript
// 인터페이스 (실제 구현은 기존 HTTP 클라이언트에 맞출 것)
function useFeedbackSubmit() {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitFeedback = async ({
    sessionId,
    agentType,
    messageId,
    feedbackType,      // "positive" | "negative"
    tags,              // string[] (긍정이면 빈 배열)
    conversationContext,
  }) => {
    setIsSubmitting(true);
    try {
      await apiClient.post('/api/feedback', {
        session_id: sessionId,
        agent_type: agentType,
        message_id: messageId,
        feedback_type: feedbackType,
        tags: tags,
        conversation_context: conversationContext || null,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      console.warn('피드백 전송 실패 (사용자 경험에 영향 없음):', error);
      // 에러를 throw하지 않는다 — UI는 성공 시와 동일하게 동작
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submitFeedback, isSubmitting };
}
```

### 스타일링 가이드

- SOHOBI의 기존 디자인 시스템(색상, 폰트, 간격)을 따른다. 기존 CSS 변수 또는 테마 토큰을 사용하라.
- 👍/👎 버튼: 기본 상태는 회색 아웃라인. 클릭 시 👍은 SOHOBI 브랜드 포인트 컬러(없으면 `#4CAF50`), 👎은 `#F44336`으로 채움.
- 태그 칩: 기본 상태는 연한 회색 배경 + 테두리. 선택 시 포인트 컬러 배경 + 흰색 텍스트.
- 전체 피드백 영역: 에이전트 응답과 시각적으로 구분되도록 상단에 얇은 구분선(`1px solid` + 연한 회색) 추가.
- 모바일 반응형 필수: 태그 칩이 화면 너비에 따라 자연스럽게 줄바꿈(flex-wrap)되도록.
- 애니메이션: 태그 영역 펼침/접힘에 부드러운 전환(150~200ms ease) 적용.

### 백엔드 API 엔드포인트

**엔드포인트:** `POST /api/feedback`

**FastAPI 라우터 구현:**

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()

class FeedbackRequest(BaseModel):
    session_id: str
    agent_type: str       # "admin" | "commercial" | "financial" | "legal" | "validator"
    message_id: str
    feedback_type: str    # "positive" | "negative"
    tags: Optional[List[str]] = []
    conversation_context: Optional[str] = None
    timestamp: str

@router.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    사용자 인라인 피드백을 Cosmos DB에 저장한다.

    기존 Cosmos DB 클라이언트를 활용하여 구현할 것.
    컨테이너명과 데이터베이스 참조 방식은 기존 코드 패턴을 따른다.
    """
    document = {
        "id": str(uuid.uuid4()),
        "session_id": feedback.session_id,
        "agent_type": feedback.agent_type,
        "message_id": feedback.message_id,
        "feedback_type": feedback.feedback_type,
        "tags": feedback.tags,
        "conversation_context": feedback.conversation_context,
        "timestamp": feedback.timestamp,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Cosmos DB 컨테이너에 문서 생성
    # 파티션 키: /agent_type
    # 기존 cosmos_client 또는 database 참조를 사용하라.
    # 예: container = database.get_container_client("feedback")
    #     container.create_item(body=document)

    return {"status": "ok", "id": document["id"]}
```

**Cosmos DB 컨테이너 설정:**
- 컨테이너명: `feedback`
- 파티션 키: `/agent_type`
- 신규 컨테이너 생성이 필요하다. 기존 Cosmos DB 데이터베이스 내에 생성하라.
- 또는 기존 컨테이너에 `doc_type: "feedback"` 필드를 추가하여 구분하는 방식도 가능 — 기존 코드베이스의 패턴을 따르라.

**라우터 등록:**
- 기존 FastAPI 앱의 라우터 등록 방식을 확인하고, 동일하게 `feedback_router`를 등록하라.
- 예: `app.include_router(feedback_router)` 또는 기존 라우터 디렉터리에 파일 추가

### 기존 코드베이스 통합 절차

1. 에이전트 응답 렌더링 컴포넌트를 찾는다.
2. 해당 컴포넌트의 return문에서 응답 텍스트 렌더링 직후 위치에 `<InlineFeedback />` 을 삽입한다.
3. `sessionId`, `agentType`, `messageId`를 해당 컴포넌트가 접근 가능한 데이터에서 추출하여 props로 전달한다.
4. `conversationContext`는 해당 대화 턴의 사용자 입력 텍스트를 전달한다 (가능하면).

```jsx
// 예시 (실제 컴포넌트명과 구조에 맞게 조정)
function AgentResponse({ message, sessionId }) {
  return (
    <div className="agent-response">
      <div className="response-content">
        {message.content}
      </div>
      <InlineFeedback
        sessionId={sessionId}
        agentType={message.agent_type}
        messageId={message.id}
        conversationContext={message.user_query}
      />
    </div>
  );
}
```

---

## 계층 3: 사용 추적 및 리포트

> **일정**: 출시 후 1~2주 내 구현. 계층 2 완료 후 착수한다.

### 3-A: 사용 이벤트 추적

#### 추적 대상 이벤트

| 이벤트명 | 트리거 시점 | 수집 데이터 |
|---|---|---|
| `agent_query` | 사용자가 에이전트에 질문 전송 | session_id, agent_type, timestamp |
| `agent_response_view` | 에이전트 응답 렌더링 완료 | session_id, agent_type, response_length, timestamp |
| `feature_discovery` | 사용자가 특정 기능 페이지 최초 방문 | session_id, feature_name, source, timestamp |
| `checklist_check` | 체크리스트 항목 체크/해제 | session_id, checklist_item_id, checked, timestamp |
| `report_view` | 사용 리포트 페이지 방문 | session_id, timestamp |
| `report_recommendation_click` | 리포트 내 추천 기능 클릭 | session_id, recommended_feature, timestamp |

#### 프론트엔드 이벤트 전송 유틸

```javascript
// utils/trackEvent.js
export async function trackEvent(eventName, payload) {
  try {
    await apiClient.post('/api/events', {
      event_name: eventName,
      ...payload,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.warn('이벤트 추적 실패:', error);
    // 추적 실패가 사용자 경험을 방해하지 않는다
  }
}

// 사용 예시
trackEvent('agent_query', {
  session_id: currentSessionId,
  agent_type: 'commercial',
});
```

#### 백엔드 이벤트 저장 엔드포인트

```python
@router.post("/api/events")
async def track_event(event: dict):
    """
    사용 이벤트를 저장한다.

    저장 방식 두 가지 중 기존 코드베이스에 맞는 것을 선택:
    1. Cosmos DB 'usage_events' 컨테이너 (쿼리/집계가 필요할 때)
    2. Azure Blob Storage에 JSON Lines 형식으로 append (단순 로그 적재)

    권장: 리포트 생성에 집계 쿼리가 필요하므로 Cosmos DB를 우선 사용.
    """
    document = {
        "id": str(uuid.uuid4()),
        **event,
        "created_at": datetime.utcnow().isoformat(),
    }
    # Cosmos DB 'usage_events' 컨테이너에 저장
    # 파티션 키: /session_id
    return {"status": "ok"}
```

**Cosmos DB 컨테이너 설정:**
- 컨테이너명: `usage_events`
- 파티션 키: `/session_id`

#### 이벤트 삽입 지점

기존 코드에서 아래 시점을 찾아 `trackEvent` 호출을 삽입하라:

1. **`agent_query`**: 사용자가 메시지를 전송하는 함수 (send, submit 등) 내부
2. **`agent_response_view`**: 에이전트 응답이 DOM에 렌더링된 후 (`useEffect` 활용)
3. **`feature_discovery`**: 각 기능 페이지 컴포넌트의 마운트 시점 (`useEffect([], [])`)

---

### 3-B: 기능별 사용 체크리스트

#### 체크리스트 데이터 정의

```javascript
// constants/checklistItems.js
export const STARTUP_CHECKLIST = [
  {
    id: 'biz_registration',
    label: '사업자등록 안내 확인',
    description: '개인/법인 사업자등록 절차와 필요 서류를 확인합니다.',
    agent: 'admin',
    autoCheckKeywords: ['사업자등록', '사업자 등록', '통신판매업'],
  },
  {
    id: 'location_analysis',
    label: '희망 입지 상권 분석',
    description: '목표 지역의 유동인구, 경쟁 업체, 임대료 수준을 분석합니다.',
    agent: 'commercial',
    autoCheckKeywords: ['상권', '입지', '유동인구', '임대료'],
  },
  {
    id: 'cost_simulation',
    label: '초기 투자 비용 시뮬레이션',
    description: '인테리어, 장비, 보증금 등 초기 투자 비용을 산출합니다.',
    agent: 'financial',
    autoCheckKeywords: ['초기 비용', '투자 비용', '인테리어 비용', '보증금'],
  },
  {
    id: 'revenue_forecast',
    label: '예상 매출/손익 시뮬레이션',
    description: '월별 예상 매출과 손익분기점을 시뮬레이션합니다.',
    agent: 'financial',
    autoCheckKeywords: ['매출', '손익', '수익', '손익분기'],
  },
  {
    id: 'hygiene_education',
    label: '위생교육 이수 안내 확인',
    description: '식품위생교육 이수 방법과 일정을 확인합니다.',
    agent: 'admin',
    autoCheckKeywords: ['위생교육', '식품위생', '위생 교육'],
  },
  {
    id: 'business_permit',
    label: '영업신고 절차 확인',
    description: '영업신고서 제출 절차와 필요 서류를 확인합니다.',
    agent: 'admin',
    autoCheckKeywords: ['영업신고', '영업 신고', '영업허가'],
  },
  {
    id: 'legal_review',
    label: '관련 법규 검토',
    description: '업종별 관련 법률과 규정을 검토합니다.',
    agent: 'legal',
    autoCheckKeywords: ['법률', '법규', '규정', '식품위생법', '조례'],
  },
  {
    id: 'final_validation',
    label: '최종 검증 리포트 생성',
    description: '전체 창업 준비 상태를 종합 검증합니다.',
    agent: 'validator',
    autoCheckKeywords: ['최종 검증', '검증 리포트', '종합 검증'],
  },
];
```

#### 체크리스트 UI 컴포넌트

```
src/
  components/
    checklist/
      StartupChecklist.jsx     ← 체크리스트 메인 컴포넌트
      ChecklistItem.jsx        ← 개별 항목 (체크박스 + 라벨 + 설명)
      ChecklistProgress.jsx    ← 상단 프로그레스 바
      useChecklistState.js     ← 체크 상태 관리 훅 (Cosmos DB 동기화)
```

**UI 와이어프레임:**
```
┌──────────────────────────────────────────────────┐
│  🎯 창업 준비 체크리스트                           │
│                                                  │
│  ████████████░░░░░░░░  5/8 완료 (62%)            │
│                                                  │
│  ✅ 사업자등록 안내 확인                     [자동] │
│  ✅ 희망 입지 상권 분석                     [자동] │
│  ✅ 초기 투자 비용 시뮬레이션               [자동] │
│  ✅ 예상 매출/손익 시뮬레이션               [자동] │
│  ✅ 위생교육 이수 안내 확인                 [수동] │
│  ⬜ 영업신고 절차 확인                             │
│     └ "영업신고 절차를 알아보세요" [바로가기 →]     │
│  ⬜ 관련 법규 검토                                │
│  ⬜ 최종 검증 리포트 생성                          │
└──────────────────────────────────────────────────┘
```

**체크 상태 저장 (Cosmos DB):**
```json
{
  "id": "checklist_{session_id}",
  "session_id": "...",
  "items": {
    "biz_registration": { "checked": true, "source": "auto", "checked_at": "..." },
    "location_analysis": { "checked": true, "source": "auto", "checked_at": "..." },
    "hygiene_education": { "checked": true, "source": "manual", "checked_at": "..." },
    "business_permit": { "checked": false }
  },
  "updated_at": "..."
}
```

**자동 체크 로직 (백엔드):**
- 에이전트가 응답을 생성할 때, 사용자의 질문 텍스트를 `autoCheckKeywords`와 대조
- 키워드 매칭 시 해당 체크리스트 항목을 `source: "auto"`로 체크 처리
- 이 로직은 기존 에이전트 응답 파이프라인에 후처리(post-processing) 단계로 추가

**수동 체크:**
- 사용자가 체크리스트 UI에서 직접 체크/해제 가능
- 수동 체크 시 `source: "manual"`로 기록

**API 엔드포인트:**

```python
@router.get("/api/checklist/{session_id}")
async def get_checklist(session_id: str):
    """세션의 체크리스트 상태를 조회한다."""
    # Cosmos DB에서 checklist_{session_id} 문서 조회
    pass

@router.patch("/api/checklist/{session_id}")
async def update_checklist(session_id: str, item_id: str, checked: bool):
    """체크리스트 항목을 수동으로 체크/해제한다."""
    # Cosmos DB 문서의 해당 항목 업데이트
    pass
```

#### 체크리스트 배치 위치

- 메인 대시보드 또는 사이드바에 상시 노출
- 또는 별도 탭/페이지(`/checklist`)로 구현
- 기존 UI 레이아웃을 확인하여 가장 자연스러운 위치에 배치하라

---

### 3-C: 사용 리포트 자동 생성

#### 리포트 데이터 구조

```json
{
  "session_id": "...",
  "summary": {
    "total_conversations": 23,
    "most_used_agent": { "type": "admin", "label": "행정 절차 안내", "count": 12 },
    "agent_usage": {
      "admin": 12,
      "commercial": 5,
      "financial": 4,
      "legal": 1,
      "validator": 1
    },
    "last_active": "2026-04-05T14:30:00+09:00",
    "first_active": "2026-04-01T10:00:00+09:00"
  },
  "checklist": {
    "completed": 5,
    "total": 8,
    "percentage": 62,
    "items": { /* 3-B의 체크리스트 상태 */ }
  },
  "recommendations": [
    {
      "feature": "business_permit",
      "label": "영업신고 절차 확인",
      "reason": "아직 확인하지 않은 필수 항목입니다.",
      "agent": "admin"
    }
  ],
  "feedback_summary": {
    "total_feedbacks": 8,
    "positive_rate": 0.75,
    "top_negative_tags": ["not_relevant"]
  }
}
```

#### 리포트 UI 컴포넌트

```
src/
  components/
    report/
      UsageReport.jsx          ← 메인 리포트 페이지
      ReportSummary.jsx        ← 상단 요약 카드 (대화 횟수, 가장 많이 사용한 기능 등)
      AgentUsageChart.jsx      ← 에이전트별 사용 비율 차트 (간단한 바 차트)
      ChecklistProgress.jsx    ← 체크리스트 진행률 (3-B의 컴포넌트 재사용)
      Recommendations.jsx      ← "다음 단계 추천" 카드 목록
```

**UI 와이어프레임:**
```
┌──────────────────────────────────────────────────┐
│  📊 나의 SOHOBI 사용 리포트                        │
│                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐  │
│  │ 총 대화      │ │ 가장 많이   │ │ 마지막     │  │
│  │   23회      │ │ 행정 절차   │ │ 4월 5일    │  │
│  └─────────────┘ └─────────────┘ └────────────┘  │
│                                                  │
│  ── 기능별 사용 현황 ────────────────────────────  │
│  행정 절차   ████████████████  12회               │
│  상권 분석   ██████████  5회                      │
│  재무 시뮬   ████████  4회                        │
│  법률 검색   ██  1회                              │
│  최종 검증   ██  1회                              │
│                                                  │
│  ── 창업 준비 진행률 ────────────────────────────  │
│  ████████████░░░░░░░░  62% (5/8)                 │
│  [체크리스트 전체 보기 →]                          │
│                                                  │
│  ── 다음 단계 추천 ──────────────────────────────  │
│  💡 영업신고 절차를 확인해 보세요  [바로가기 →]     │
│  💡 최종 검증 리포트를 생성해 보세요 [바로가기 →]   │
└──────────────────────────────────────────────────┘
```

#### 백엔드 API

```python
@router.get("/api/report/{session_id}")
async def get_usage_report(session_id: str):
    """
    세션의 사용 리포트 데이터를 집계하여 반환한다.

    집계 대상:
    1. usage_events 컨테이너에서 session_id별 에이전트 사용 횟수 집계
    2. feedback 컨테이너에서 session_id별 피드백 요약 집계
    3. checklist 문서에서 진행률 조회
    4. 미완료 체크리스트 항목을 기반으로 추천 목록 생성

    Cosmos DB 쿼리 예시:
    SELECT c.agent_type, COUNT(1) as count
    FROM c
    WHERE c.session_id = @session_id AND c.event_name = 'agent_query'
    GROUP BY c.agent_type
    """
    pass
```

#### 리포트 접근 경로

- 별도 페이지: `/my-report` 또는 `/report`
- 또는 기존 대시보드/설정 페이지 내 탭으로 추가
- 기존 라우팅 구조를 확인하여 적합한 방식을 선택하라

---

### 3-D: 인앱 로드맵 투표 위젯

> **일정**: 출시 후 1~2개월 내 구현. 우선순위 가장 낮음.

#### 기능 후보 목록

```javascript
// constants/roadmapFeatures.js
export const ROADMAP_FEATURES = [
  { id: 'inventory',       label: '재고 관리 도우미',                icon: '📦' },
  { id: 'revenue_dashboard', label: '매출/비용 분석 대시보드',        icon: '📊' },
  { id: 'tax_guide',       label: '세무/회계 안내',                 icon: '🧾' },
  { id: 'hr_guide',        label: '직원 채용/노무 관리 가이드',      icon: '👥' },
  { id: 'delivery_pos',    label: '배달앱/POS 연동 매출 통합',       icon: '📱' },
  { id: 'safety_checklist', label: '위생/안전 점검 체크리스트',       icon: '✅' },
  { id: 'crm',             label: '단골 고객 관리 (CRM)',           icon: '💎' },
  { id: 'menu_pricing',    label: '메뉴 원가 계산 및 가격 최적화',   icon: '🍽️' },
];
```

#### UI 와이어프레임

```
┌────────────────────────────────────────────┐
│  🗳️ 다음에 추가되었으면 하는 기능           │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ 📦 재고 관리 도우미           ▲ 24표 │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ 📊 매출/비용 분석 대시보드     ▲ 18표 │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ 🧾 세무/회계 안내             ▲ 15표 │  │
│  └──────────────────────────────────────┘  │
│  ...                                       │
└────────────────────────────────────────────┘
```

- 사용자당 기능당 1표 제한 (토글 — 재클릭 시 취소)
- 투표 수 기준 내림차순 정렬
- ▲ 버튼 클릭 시 즉시 반영 (옵티미스틱 업데이트)

#### 데이터 구조 (Cosmos DB)

```json
// 개별 투표 문서
{
  "id": "vote_{feature_id}_{session_id}",
  "feature_id": "inventory",
  "session_id": "...",
  "voted_at": "2026-04-15T10:00:00+09:00"
}

// 또는 기능별 집계 문서 (성능 최적화)
{
  "id": "feature_votes_{feature_id}",
  "feature_id": "inventory",
  "vote_count": 24,
  "voters": ["session_1", "session_2", ...]
}
```

#### API 엔드포인트

```python
@router.get("/api/roadmap/votes")
async def get_roadmap_votes(session_id: str):
    """모든 기능의 투표 현황과 현재 사용자의 투표 상태를 반환한다."""
    pass

@router.post("/api/roadmap/vote")
async def toggle_vote(feature_id: str, session_id: str):
    """기능에 투표하거나 투표를 취소한다. (토글)"""
    pass
```

---

## 구현 체크리스트

### 즉시 구현 (계층 2)

- [ ] 사전 작업: 코드베이스 파악 (응답 렌더링 컴포넌트, 세션 관리, HTTP 클라이언트, Cosmos DB 패턴, 디자인 토큰)
- [ ] `feedbackConstants.js` 생성
- [ ] `useFeedbackSubmit.js` 훅 구현
- [ ] `FeedbackTags.jsx` 컴포넌트 구현
- [ ] `InlineFeedback.jsx` 컴포넌트 구현
- [ ] `POST /api/feedback` FastAPI 엔드포인트 구현
- [ ] Cosmos DB `feedback` 컨테이너 생성
- [ ] 에이전트 응답 컴포넌트에 `InlineFeedback` 통합
- [ ] 스타일링 (기존 디자인 시스템 적용)
- [ ] 모바일 반응형 테스트

### 단기 구현 (계층 3-A, 3-B, 3-C)

- [ ] `trackEvent` 유틸 구현
- [ ] `POST /api/events` 엔드포인트 구현
- [ ] Cosmos DB `usage_events` 컨테이너 생성
- [ ] 기존 코드에 이벤트 추적 호출 삽입
- [ ] 체크리스트 상수 및 상태 관리 훅 구현
- [ ] 체크리스트 UI 컴포넌트 구현
- [ ] 자동 체크 로직 (백엔드 후처리) 구현
- [ ] 체크리스트 API 엔드포인트 구현
- [ ] 사용 리포트 API 엔드포인트 구현
- [ ] 사용 리포트 UI 컴포넌트 구현
- [ ] 리포트 페이지 라우팅 추가

### 중기 구현 (계층 3-D)

- [ ] 로드맵 투표 API 구현
- [ ] 로드맵 투표 위젯 UI 구현

---

## 공통 원칙

1. **피드백/추적 실패가 사용자 경험을 방해해서는 안 된다.** 모든 피드백·이벤트 전송은 try-catch로 감싸고, 실패 시 console.warn만 남긴다.
2. **기존 코드 패턴을 따른다.** 새로운 라이브러리나 상태 관리 방식을 도입하지 말고, 기존 프로젝트에서 사용 중인 패턴으로 구현한다.
3. **상수를 분리한다.** 태그 목록, 체크리스트 항목, 로드맵 기능 목록 등은 별도 상수 파일로 분리하여, 문구 변경이나 A/B 테스트가 용이하도록 한다.
4. **모바일 반응형은 필수다.** SOHOBI의 주 사용자인 소상공인은 모바일 사용 비율이 높다.
5. **한국어 UI 문구를 사용한다.** 모든 사용자 대면 텍스트는 한국어로, 코드 내부 변수명과 주석은 영어로 작성한다.
6. **개인정보 보호**: 피드백·이벤트 데이터에 PII가 포함되지 않도록 한다. `conversationContext`에 사용자 입력 원문을 저장할 경우, 개인 식별 정보(이름, 전화번호, 주소 등)가 포함될 수 있으므로, 저장 전 PII 필터링 여부를 검토하라. (현재 백엔드에 PII 필터링이 미구현 상태이므로, 최소한 `conversationContext` 저장을 선택적으로 만들어라.)
