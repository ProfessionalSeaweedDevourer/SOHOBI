# devAuth 콘솔 bypass 취약점 수정 플랜

## Context

`sessionStorage.setItem("sohobi_dev_auth", "1")` 한 줄로 개발자 모드에 비밀번호 없이 진입 가능.
원인: `isDevAuthenticated()`가 값이 `"1"`인지만 확인하므로, 키 이름만 알면 누구든 콘솔에서 조작 가능.

## 해결 전략: HMAC 기반 세션 토큰 (방법 B)

인증 성공 시 랜덤 nonce를 생성하고, `STORED_HASH`를 키로 HMAC-SHA256(nonce)을 계산해 토큰으로 저장.
검증 시 nonce + STORED_HASH로 토큰을 재계산해 비교.

**남은 한계 (클라이언트 전용의 근본 한계)**: 번들에서 `STORED_HASH`를 추출한 공격자는 동일한 crypto API로 토큰을 직접 생성 가능. 방법 B는 "단순 콘솔 한 줄 조작"을 "번들 분석 + crypto API 코딩"으로 난이도를 높이는 것이며, 완전한 차단은 백엔드 검증(방법 C)으로만 가능.

## 수정 파일 (4개)

### 1. `frontend/src/utils/devAuth.js`

**변경사항:**
- `SESSION_NONCE_KEY = "sohobi_dev_nonce"` 상수 추가
- `setDevAuthenticated(hashHex)` → async, hashHex 파라미터 추가. nonce 생성 → HMAC-SHA256(key=hashHex, data=nonce) → nonce+token sessionStorage 저장
- `isDevAuthenticated()` → async. nonce+token 읽어 HMAC 재계산 후 `crypto.subtle.verify()`로 비교
- `clearDevAuth()` → SESSION_NONCE_KEY도 함께 제거
- `checkDevPassword(input)` → 반환값 `{ ok: boolean, hash: string }` 구조로 변경

### 2. `frontend/src/pages/DevLogin.jsx`

- **line 21**: `useEffect` 내 `isDevAuthenticated()` → `isDevAuthenticated().then(ok => { if (ok) navigate(...) })`
- **line 34**: `const ok = await checkDevPassword(password)` → `const { ok, hash } = await checkDevPassword(password)`
- **line 36**: `setDevAuthenticated()` → `await setDevAuthenticated(hash)`

### 3. `frontend/src/components/RequireDevAuth.jsx`

동기 렌더에서 async 검증으로 전환. `useState("checking") + useEffect` 패턴 도입:
```jsx
const [authState, setAuthState] = useState("checking");
useEffect(() => {
  isDevAuthenticated().then(ok => setAuthState(ok ? "ok" : "fail"));
}, []);
if (authState === "checking") return null;
if (authState === "fail") return <Navigate to="/dev/login" ... />;
return children;
```

### 4. `frontend/src/pages/Home.jsx`

- **line 41**: `function handleModeClick(path)` → `async function handleModeClick(path)`
- **line 42**: `!isDevAuthenticated()` → `!(await isDevAuthenticated())`

## 검증 방법

1. `npm run dev` 실행
2. `/dev/login`에서 올바른 비밀번호 입력 → `/dev` 진입 확인
3. 콘솔에서 `sessionStorage.setItem("sohobi_dev_auth", "1")` 후 `/dev` 직접 URL 접근 → `/dev/login`으로 리다이렉트되어야 함 (**핵심 검증**)
4. 콘솔에서 `sessionStorage.setItem("sohobi_dev_auth", "1")` 후 홈에서 개발자 모드 클릭 → `/dev/login`으로 이동해야 함
5. 정상 로그인 후 탭 새로고침 → 세션 유지 확인
6. 로그아웃 버튼 → `sohobi_dev_auth`, `sohobi_dev_nonce` 두 키 모두 삭제 확인
