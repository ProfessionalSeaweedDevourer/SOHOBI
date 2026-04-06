# 브라우저 탭 파비콘 교체: vite.svg → sohobi_logo_small.png

## Context
브라우저 탭 아이콘이 기본 Vite 로고(vite.svg)로 표시되고 있음.
SOHOBI 로고 이미지(sohobi_logo_small.png)로 교체하여 브랜드 아이덴티티를 반영.

## 변경 사항

### 1. PNG 파일을 public/ 에 복사
- `frontend/dist/sohobi_logo_small.png` → `frontend/public/sohobi_logo_small.png`
- `dist/`는 빌드 산출물 폴더이며, Vite 개발 서버는 `public/`에서 정적 파일을 서빙함

### 2. index.html 파비콘 링크 수정
**파일**: `frontend/index.html` (line 5)

변경 전:
```html
<link rel="icon" type="image/svg+xml" href="/vite.svg" />
```

변경 후:
```html
<link rel="icon" type="image/png" href="/sohobi_logo_small.png" />
```

## 검증
- `npm run dev` 실행 후 브라우저에서 탭 아이콘 확인
- 빌드 시 `npm run build` → `dist/` 에 PNG가 포함되는지 확인
