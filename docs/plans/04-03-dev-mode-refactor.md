# Dev Mode 재편 계획

## Context

Features 페이지 연결이 제거되면서 `/dev/login` → `/dev` / `/dev/logs`로 이어지는 GUI 입장 경로가 사라졌다. 그러나 라우팅 자체는 살아있고 SHA-256 패스워드 인증으로 보호되어 있어, URL을 아는 사람은 여전히 접근 가능하다.

현재 사용자 모드(UserChat)와 개발자 모드(DevChat)의 정보 노출 차이:
- 사용자: 간단한 스피너 + 최종 응답 (등급 B일 때 경고 배너)
- 개발자: 도메인/등급 배지, ProgressPanel 상세, SignoffPanel(거부 코드·이유·수정 지시문), 실행 시간(ms), 로그 뷰어 접근

핵심 판단 기준:
- **로그 뷰어**는 모든 사용자의 쿼리 데이터를 노출 → 개인정보 보호상 절대 사용자에게 공개 불가
- **URL 숨기기**는 보안 수단이 아님(Security through obscurity). 실제 보안은 패스워드 인증에서 나온다.
- 일부 메타정보(등급·도메인·검증 횟수)를 사용자에게 공개해도 보안상 문제 없음. 오히려 신뢰성을 높인다.

---

## 권장 방향: 계층형 투명성(Tiered Transparency)

### Tier 1 — 일반 사용자 (UserChat)
응답 품질 신호를 일부 개방해 신뢰성 강화. 내부 구현 디테일(코드·수정 지시문)은 비공개 유지.

**변경 대상: `frontend/src/pages/UserChat.jsx`**
- `showMeta` prop을 `false → true`로는 바꾸지 않음 (전부 공개 아님)
- 대신 ResponseCard에 새로운 `showGrade={true}` prop 추가

**변경 대상: `frontend/src/components/ResponseCard.jsx`**
- `showGrade` prop 추가:
  - 등급 배지(A/B/C) 표시 — 현재 개발자만 볼 수 있음
  - 도메인 배지는 여전히 개발자 전용 유지
  - Grade B 경고 배너는 유지

**변경 대상: `frontend/src/components/ProgressPanel.jsx`**
- `detailed=false` (사용자) 모드에서 시도 횟수 텍스트 추가:
  - 예: "검증 중… (2차 시도)"
  - 현재는 도메인 라벨 + 아이콘만 표시

**변경 없음 (사용자 모드에서 계속 비공개 유지):**
- 검증 코드 (C1-C5, F1-F5 등)
- 반려 이유·수정 지시문
- 실행 시간 (ms)
- SignoffPanel

### Tier 2 — 개발자 (DevChat + LogViewer)
현행 유지. 변경 없음.

### Dev Mode 입장 경로
현재 상태(URL 직접 입력) 유지. 별도 링크 추가하지 않음.
- 보안은 이미 `/dev/login`의 SHA-256 패스워드 인증이 담당
- 링크가 있든 없든 패스워드 없이는 접근 불가이므로, 링크를 추가해도 보안상 문제 없음
- **그러나** 사용자가 dev 링크를 볼 필요가 없으므로 추가하지 않음 (UX 간결성)

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/components/ResponseCard.jsx` | `showGrade` prop 추가, Grade 배지를 사용자 모드에서도 표시 |
| `frontend/src/pages/UserChat.jsx` | ResponseCard에 `showGrade={true}` 전달 |
| `frontend/src/components/ProgressPanel.jsx` | `detailed=false` 시 시도 횟수 텍스트 추가 |

---

## 검증 방법

1. `cd frontend && npm run dev`
2. `/user` 접속 → 질문 전송
   - ProgressPanel에서 "검증 중… (2차 시도)" 텍스트 노출 확인
   - ResponseCard에서 A/B/C 배지 표시 확인
   - 검증 코드·수정 지시문은 미표시 확인
3. `/dev/login` → 로그인 → `/dev` 접속
   - 기존 개발자 기능 전부 정상 작동 확인
   - 로그 뷰어(`/dev/logs`) 정상 작동 확인

---

## 보류/미결 사항

- 장기적으로 SignoffPanel의 "검증 N회" 요약 텍스트(코드 없이)를 사용자 모드에 노출할지 여부는 추후 결정
- 도메인 배지를 사용자에게 공개할지 여부 (현재 계획: 개발자 전용 유지)
