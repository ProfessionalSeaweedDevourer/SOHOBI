# SOHOBI 프론트엔드

SOHOBI 통합 에이전트(`integrated_PARK/`)와 연동하는 React 기반 웹 UI입니다.

---

## 기술 스택

| 항목           | 버전 |
| -------------- | ---- |
| React          | 18   |
| Vite           | 7    |
| Tailwind CSS   | 3    |
| React Router   | v6   |
| react-markdown | -    |

---

## 페이지 구성

| 경로 | 설명 |
| --- | --- |
| `/` | 홈 — 사용자 모드 / 개발자 모드 선택 |
| `/user` | 사용자 모드 — 질문 입력 및 응답 확인 |
| `/dev` | 개발자 모드 — Sign-off 판정 내역 및 루브릭 포함 |
| `/dev/logs` | 로그 뷰어 — 요청 이력 및 거부 이력 확인 |

---

## 로컬 개발 실행

### 필수 조건

- Node.js 18 이상
- `integrated_PARK/` 백엔드 서버가 **포트 8000**에서 실행 중이어야 합니다.

### 설치 및 실행

```bash
# 1. 이 폴더로 이동
cd frontend

# 2. 의존성 설치
npm install

# 3. 개발 서버 시작
npm run dev
# → http://localhost:3000 에서 접속
```

개발 서버는 `/api/*` 요청을 자동으로 `http://localhost:8000`으로 프록시합니다.
백엔드 서버 실행 방법은 [`../integrated_PARK/README.md`](../integrated_PARK/README.md)를 참고하세요.

---

## 프로덕션 빌드

```bash
npm run build
# → dist/ 폴더에 정적 파일 생성
```

---

## Vercel 배포

### 설정값

| 항목 | 값 |
|------|----|
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |

### 백엔드 연결 (필수)

Vercel에서 실행되는 프론트엔드는 `localhost:8000`에 접근할 수 없습니다.
백엔드를 별도 서버(Railway 등)에 배포한 후, 아래 환경변수를 Vercel 프로젝트에 추가해야 합니다.

**Vercel 대시보드 → 프로젝트 → Settings → Environment Variables:**

| 변수명 | 값 예시 |
|--------|---------|
| `VITE_API_URL` | `https://your-backend.railway.app` |

환경변수 설정 후 **Redeploy**를 실행해야 반영됩니다.

> 백엔드를 배포하기 전 임시 테스트가 필요하다면, ngrok 등으로 로컬 서버를 터널링한 뒤
> 해당 URL을 `VITE_API_URL`에 설정할 수 있습니다.

---

## 폴더 구조

```
frontend/
├── src/
│   ├── api.js                  백엔드 fetch 래퍼 (VITE_API_URL 환경변수 사용)
│   ├── App.jsx                 라우터 정의
│   ├── pages/
│   │   ├── Home.jsx            모드 선택 랜딩
│   │   ├── UserChat.jsx        사용자 채팅
│   │   ├── DevChat.jsx         개발자 채팅 + Sign-off 패널
│   │   └── LogViewer.jsx       로그 뷰어
│   └── components/
│       ├── ChatInput.jsx       입력창 (오류 시 내용 보존)
│       ├── ResponseCard.jsx    응답 카드 (마크다운 렌더링)
│       ├── SignoffPanel.jsx    루브릭 항목 통과/실패 아코디언
│       └── LogTable.jsx        로그 목록 및 상세 패널
├── vite.config.js              개발 서버 프록시 설정 포함
├── tailwind.config.js
└── package.json
```
