# 플랜: 랜딩 페이지 지도 링크 추가 + Cmd+L 제거 + AgentCard 클릭 기능 제거

## Context
세 가지 문제를 한 번에 수정한다:
1. 랜딩 페이지에서 지도·상권분석(`/map`)으로 직접 이동하는 링크가 없어 기능 접근성이 낮다.
2. `Cmd/Ctrl+L`이 `/dev/logs`로 이동하도록 설정되어 있으나 의도하지 않은 동작이다.
3. AgentCard 클릭 시 `/user` 상담으로 이동하는 기능도 의도하지 않은 것으로 제거한다.

---

## 변경 1 — 랜딩 히어로 CTA에 지도·상권분석 링크 추가

**파일**: `frontend/src/pages/Landing.jsx` (줄 89–102)

현재 버튼 2개 (`/user`, `/dev/logs`) 사이에 `/map` 버튼을 추가한다.

```jsx
<Link to="/map">
  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
    <Button size="lg" variant="outline" className="px-10 py-6 text-lg glass border-2 shadow-elevated">
      지도·상권분석 보기
    </Button>
  </motion.div>
</Link>
```

---

## 변경 2 — Cmd+L 키보드 단축키 제거

**파일**: `frontend/src/components/KeyboardShortcuts.jsx`

1. `case 'l':` 블록(줄 30–36) 전체 삭제
2. 줄 13 도움말 toast 텍스트에서 `⌘/Ctrl+L (로그)` 제거

---

## 변경 3 — AgentCard 클릭 시 상담 이동 기능 제거

**파일**: `frontend/src/components/AgentCard.jsx`

- `useNavigate` import 제거
- `toast` import 제거 (AgentCard에서만 사용 중이면)
- `handleClick` 함수 전체 삭제
- `motion.div`의 `onClick={handleClick}` 제거
- `cursor-pointer` 클래스 제거

카드는 시각적 정보 표시 역할만 하고, 클릭 동작은 없애다.

---

## 검증

```bash
cd frontend && npm run dev
```

- 랜딩 히어로 CTA: "지도·상권분석 보기" 버튼 → `/map` 정상 이동
- `Cmd+L` 입력 → 아무 동작 없음 (브라우저 기본 주소창 포커스)
- `Cmd+/` toast → `Cmd+L` 언급 없음
- AgentCard 클릭 → 아무 동작 없음 (커서도 기본 포인터)
