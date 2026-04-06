# 키보드 단축키 전면 제거 플랜

## Context

`KeyboardShortcuts.jsx`가 전역 keydown 리스너를 통해 ESC → navigate(-1), Ctrl+H → 홈, Ctrl+U → /user 이동을 처리하고 있어, 사용자가 의도하지 않은 페이지 이동이 발생함. 단축키 전반을 제거하는 것이 목표.

Enter 키로 채팅 메시지를 전송하는 기능(ChatInput.jsx, ChatPanel.jsx, CategoryPanel.jsx)은 의도된 동작이므로 유지.

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/components/KeyboardShortcuts.jsx` | 파일 삭제 (또는 빈 컴포넌트로 교체) |
| `frontend/src/App.jsx` | import 제거 + `<KeyboardShortcuts />` JSX 제거 |

## 상세 수정

### 1. `frontend/src/App.jsx`
- Line 20: `import { KeyboardShortcuts } from "./components/KeyboardShortcuts";` 삭제
- Line 54: `<KeyboardShortcuts />` 삭제

### 2. `frontend/src/components/KeyboardShortcuts.jsx`
- 파일 전체 삭제

## 유지하는 키보드 동작 (변경 없음)

- `frontend/src/components/ChatInput.jsx` — Enter로 메시지 전송
- `frontend/src/components/map/ChatPanel.jsx` — Enter로 메시지 전송
- `frontend/src/components/map/panel/CategoryPanel.jsx` — Enter로 검색 실행

## 검증

1. 앱 실행 후 각 페이지(/map, /user 등)에서 ESC 키 눌러 이동 없음 확인
2. Ctrl+H, Ctrl+U 키 눌러 이동 없음 확인
3. 채팅 입력창에서 Enter로 메시지 전송 정상 동작 확인
