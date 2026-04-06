# 개인정보처리방침 웹페이지 구현 계획

## Context
`docs/SOHOBI_Privacy_Policy_Disclaimer.md`에 작성된 개인정보처리방침 및 이용약관(면책·AUP)을
Landing 페이지와 동일한 디자인 시스템을 적용한 전용 웹페이지로 제공해야 한다.
Landing 푸터 하단에 '개인정보처리방침' 링크를 추가하여 해당 페이지로 연결한다.

---

## 수정 파일

| 파일 | 작업 |
|------|------|
| `frontend/src/pages/PrivacyPolicy.jsx` | **신규 생성** — 개인정보처리방침 전용 페이지 |
| `frontend/src/App.jsx` | `/privacy` 라우트 추가 |
| `frontend/src/pages/Landing.jsx` | 푸터에 '개인정보처리방침' 링크 추가 |

---

## 1. PrivacyPolicy.jsx 구조

### 레이아웃
Landing.jsx와 동일한 패턴 사용:
- `<AnimatedBackground />` (배경 애니메이션 재사용)
- `<ThemeToggle />` 포함 sticky 헤더 (SOHOBI 로고 + "홈으로" 버튼)
- 본문 콘텐츠 섹션
- 동일한 glass footer

### 헤더
```jsx
<motion.header className="glass border-b border-white/20 sticky top-0 z-50">
  SOHOBI 로고 | ThemeToggle | Link to="/" 홈으로 버튼
</motion.header>
```

### 히어로 배너
```jsx
<section className="container mx-auto px-4 py-20 text-center">
  <motion.div> {/* 뱃지: FileText 아이콘 + "법적 고지" */} </motion.div>
  <h1 className="gradient-text">개인정보처리방침</h1>
  <p className="text-muted-foreground">버전 1.0 · 시행일 2025년 4월</p>
</section>
```

### 본문 — 두 파트를 glass 카드 레이아웃으로

**Part 1: 개인정보처리방침 (8개 조항)**
- 각 조항을 `<motion.div whileInView>` glass 카드로 렌더링
- 조항 번호를 brand-blue 원형 배지로 표시
- 조항 제목 굵게, 내용은 `text-muted-foreground`

**Part 2: 면책 및 이용 정책 (AUP, 5개 조항)**
- 동일한 카드 패턴, 구분선(border-t)으로 파트 분리
- 섹션 타이틀 `gradient-text`

### 연락처 CTA 박스
```jsx
<div className="glass rounded-2xl p-8 text-center">
  support@sohobi.kr | 3영업일 내 회신
</div>
```

### 사용할 디자인 토큰
- `glass`, `gradient-text`, `shadow-elevated`
- `animate-float`, `animate-shimmer`
- `hover-glow-blue`, `transition-glow`
- `var(--brand-blue)`, `var(--brand-teal)`
- Framer Motion: `initial/animate`, `whileInView viewport={{ once: true }}`

---

## 2. App.jsx — 라우트 추가

`frontend/src/App.jsx`에서 기존 라우트 목록에 추가:

```jsx
import PrivacyPolicy from './pages/PrivacyPolicy';
// ...
<Route path="/privacy" element={<PrivacyPolicy />} />
```

위치: `/map` 라우트 아래, catch-all `*` 위.

---

## 3. Landing.jsx — 푸터 링크 추가

현재 푸터 (line 251–256):
```jsx
<footer className="glass border-t border-white/20 py-12 backdrop-blur-xl">
  <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
    <p className="mb-2">© 2026 SOHOBI.</p>
    <p>소상공인을 위한 AI 컨설팅 플랫폼</p>
  </div>
</footer>
```

변경 후:
```jsx
<footer className="glass border-t border-white/20 py-12 backdrop-blur-xl">
  <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
    <p className="mb-2">© 2026 SOHOBI.</p>
    <p className="mb-3">소상공인을 위한 AI 컨설팅 플랫폼</p>
    <Link to="/privacy" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
      개인정보처리방침
    </Link>
  </div>
</footer>
```

---

## 검증 방법

1. `cd frontend && npm run dev` 실행
2. `http://localhost:5173/` → 랜딩 푸터에 '개인정보처리방침' 링크 확인
3. 링크 클릭 → `/privacy` 페이지 이동 확인
4. 다크/라이트 테마 전환 시 디자인 정상 동작 확인
5. 모바일 반응형 (md 브레이크포인트) 확인
6. `npm run build` — 빌드 에러 없음 확인
