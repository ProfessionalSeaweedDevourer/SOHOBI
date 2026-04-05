# 개발자 모드 접근 제어 — 별도 로그인 구현

## Context
릴리즈 환경에서 `/dev`(DevChat)와 `/dev/logs`(LogViewer)는 현재 완전히 공개 라우트다. URL을 직접 입력하면 누구든 접근할 수 있어 내부 로그·루브릭 판정 내역이 노출된다. 실 서비스 배포 전에 이 두 라우트에 별도 비밀번호 인증을 적용해야 한다.

## 구현 방식 개요

- **인증 저장소**: `sessionStorage` — 탭 닫으면 자동 만료, 별도 TTL 로직 불필요
- **비밀번호 검증**: `SubtleCrypto.subtle.digest("SHA-256", ...)` — 빌드 시 `VITE_DEV_PASSWORD_HASH` 환경변수에 해시값만 번들에 포함, 평문 노출 없음
- **패키지 추가 없음**: 기존 React Router v7 + Web Crypto API만 사용
- **신규 라우트**: `/dev/login` (공개) — 인증 후 원래 목적지로 redirect

## 신규 파일 (3개)

### 1. `frontend/src/utils/devAuth.js`
인증 헬퍼 유틸리티 (React 의존 없음).

```js
const SESSION_KEY = "sohobi_dev_auth";
const STORED_HASH = import.meta.env.VITE_DEV_PASSWORD_HASH ?? "";

export function isDevAuthenticated() {
  return sessionStorage.getItem(SESSION_KEY) === "1";
}

export function setDevAuthenticated() {
  sessionStorage.setItem(SESSION_KEY, "1");
}

export function clearDevAuth() {
  sessionStorage.removeItem(SESSION_KEY);
}

export async function checkDevPassword(input) {
  if (!STORED_HASH) return false;
  const encoded = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoded);
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return hashHex === STORED_HASH;
}
```

### 2. `frontend/src/components/RequireDevAuth.jsx`
라우트 가드 컴포넌트.

```jsx
import { Navigate, useLocation } from "react-router-dom";
import { isDevAuthenticated } from "../utils/devAuth";

export default function RequireDevAuth({ children }) {
  const location = useLocation();
  if (!isDevAuthenticated()) {
    return <Navigate to="/dev/login" state={{ from: location }} replace />;
  }
  return children;
}
```

### 3. `frontend/src/pages/DevLogin.jsx`
비밀번호 입력 페이지 (기존 Tailwind 스타일 유지, violet 계열).

주요 동작:
- 이미 인증된 경우 `useEffect`로 즉시 `/dev` redirect
- `checkDevPassword(input)` 비동기 호출 → 성공 시 `setDevAuthenticated()` 후 `navigate(destination, { replace: true })`
- 실패 시 "비밀번호가 올바르지 않습니다." 에러 메시지
- "← 홈으로 돌아가기" 링크 포함
- `VITE_DEV_PASSWORD_HASH` 미설정 시 항상 false (안전한 기본값)

## 수정 파일 (2개)

### `frontend/src/App.jsx`
- `DevLogin`과 `RequireDevAuth` import 추가
- `/dev/login` 공개 라우트 추가 (`/dev` 앞에 위치)
- `/dev`와 `/dev/logs`를 `<RequireDevAuth>` 로 감싸기

```jsx
// 변경 전
<Route path="/dev" element={<DevChat />} />
<Route path="/dev/logs" element={<LogViewer />} />

// 변경 후
<Route path="/dev/login" element={<DevLogin />} />
<Route path="/dev" element={<RequireDevAuth><DevChat /></RequireDevAuth>} />
<Route path="/dev/logs" element={<RequireDevAuth><LogViewer /></RequireDevAuth>} />
```

### `frontend/src/pages/Home.jsx`
- `isDevAuthenticated` import 추가
- `onClick={() => navigate(m.path)}` → `onClick={() => handleModeClick(m.path)}`
- `handleModeClick` 함수 추가:

```jsx
function handleModeClick(path) {
  if (path === "/dev" && !isDevAuthenticated()) {
    navigate("/dev/login", { state: { from: { pathname: "/dev" } } });
    return;
  }
  navigate(path);
}
```
> Home에서 미리 분기하는 이유: RequireDevAuth만 쓰면 홈→/dev→/dev/login으로 히스토리 엔트리가 2개 생겨 뒤로가기 UX가 나빠짐.

## 환경변수 설정

```bash
# SHA-256 해시 생성 (Node)
node -e "const{createHash}=require('crypto'); console.log(createHash('sha256').update('YOUR_PASSWORD').digest('hex'))"
```

- `frontend/.env.local` (git 미포함): `VITE_DEV_PASSWORD_HASH=<hex값>`
- `frontend/.env.example` (git 포함): 변수명과 생성법 주석만 기재

Azure 배포 시 빌드 환경(GitHub Actions Secret 또는 Azure Static Web Apps 설정)에 동일 변수 추가 필요.

## 선택 추가: 로그아웃 버튼

`DevChat.jsx` 헤더에 로그아웃 버튼 추가 (권장):

```jsx
import { clearDevAuth } from "../utils/devAuth";
// 헤더 내부:
<button onClick={() => { clearDevAuth(); navigate("/"); }}>로그아웃</button>
```

## 수정 파일 목록

| 파일 | 작업 |
|---|---|
| `frontend/src/utils/devAuth.js` | 신규 생성 |
| `frontend/src/components/RequireDevAuth.jsx` | 신규 생성 |
| `frontend/src/pages/DevLogin.jsx` | 신규 생성 |
| `frontend/src/App.jsx` | 라우트 수정 |
| `frontend/src/pages/Home.jsx` | `handleModeClick` 추가 |
| `frontend/.env.local` | `VITE_DEV_PASSWORD_HASH` 추가 (git 미포함) |
| `frontend/.env.example` | 변수 문서화 |

## 검증 방법

1. `npm run dev` 실행
2. `/dev` 직접 접근 → `/dev/login` redirect 확인
3. 틀린 비밀번호 입력 → 에러 메시지 확인
4. 맞는 비밀번호 입력 → `/dev` 진입 확인
5. `/dev/logs` 직접 접근 → 마찬가지로 login redirect 확인
6. DevChat 내에서 "📋 로그 뷰어" 버튼 클릭 → 인증된 상태로 바로 진입 확인
7. 탭 닫고 재접속 → 다시 로그인 요구 확인
