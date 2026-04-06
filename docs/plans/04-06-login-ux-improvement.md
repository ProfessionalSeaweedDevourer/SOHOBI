# 플랜: 로그인 유도 UX 개선

## Context

UserChat 페이지 헤더에 로그인 버튼이 있지만, 비로그인 유저는 로그인의 이점을 알 수 없다.
로그인 시 얻을 수 있는 혜택(상담 기록 저장, 내 로그, 리포트 조회)을 자연스럽게 노출해
이탈 없이 로그인 전환율을 높이는 것이 목표.

---

## 접근 방안 검토

| 방안 | 장점 | 단점 |
|------|------|------|
| **A. 첫 응답 후 인라인 카드** | 가장 자연스러운 타이밍 (AI가 가치를 제공한 직후) | 대화 흐름에 카드 하나 추가 |
| B. 헤더 로그인 버튼 hover 툴팁 | 코드 최소화 | 모바일 불친화적, 발견 가능성 낮음 |
| C. 타이머 기반 토스트 | 즉시 노출 | 가치 제공 전 방해 느낌 |
| D. 3번째 질문 직전 모달 | 강제 노출 | 사용 중단 / 거부감 위험 |

**선택: A (첫 응답 후 인라인 카드)**
- 유저가 AI의 가치를 경험한 직후가 전환 유도 최적 타이밍
- 블로킹이 없어 거부감 없음
- 한 번 닫으면 localStorage에 기록해 재노출 없음

---

## 구현 계획

### 새 컴포넌트: `LoginNudgeCard`

파일: `frontend/src/components/LoginNudgeCard.jsx`

```
[ 💾 이 상담, 기록으로 남기고 싶으신가요?                         ✕ ]
  로그인하면 오늘 상담 내용이 자동 저장됩니다.

  ✅ 내 로그 — 지난 상담 내역 언제든 재열람
  ✅ 내 리포트 — 질문 유형·통계 분석
  ✅ 체크리스트 동기화 — 창업 진행 현황 저장

  [ Google로 로그인 ]
```

- 스타일: 기존 `.glass` + `rounded-2xl border` 패턴 사용
- brand-blue 계열 배경 (`rgba(8,145,178,0.07)`)
- dismiss 시 `localStorage.setItem("sohobi_login_nudge_dismissed", "1")`

### UserChat.jsx 수정

1. `showLoginNudge` state 추가:
   ```js
   const [showLoginNudge, setShowLoginNudge] = useState(
     () => !user && !localStorage.getItem("sohobi_login_nudge_dismissed")
   );
   ```

2. 메시지 목록 렌더링 부분에서 첫 번째 성공 응답 다음에 카드 삽입:
   ```jsx
   {messages.map((msg, i) => (
     <>
       <ResponseCard key={i} ... />
       {i === 0 && showLoginNudge && (
         <LoginNudgeCard onLogin={login} onDismiss={() => { ... }} />
       )}
     </>
   ))}
   ```

---

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/components/LoginNudgeCard.jsx` | 신규 생성 |
| `frontend/src/pages/UserChat.jsx` | `showLoginNudge` state + 카드 삽입 |

---

## 검증 방법

1. 브라우저 시크릿 창으로 `/user` 접속 (비로그인)
2. 질문 하나 전송 → 응답 카드 아래 LoginNudgeCard 노출 확인
3. ✕ 버튼 클릭 → 카드 사라짐, localStorage `sohobi_login_nudge_dismissed=1` 확인
4. 새로고침 → 카드 미표시 확인
5. "Google로 로그인" 버튼 클릭 → Google OAuth 흐름 진입 확인
6. 로그인 유저로 접속 시 → 카드 표시 안 됨 확인
