# PR #129 정리 가이드 — CHOI2 브랜치 혼입 커밋 분리

## 상황 요약

PR #129의 7개 커밋 중 **5개가 PARK 브랜치 작업**입니다 (작성자: `ProfessionalSeaweedDevourer`).
delta115zx 본인의 커밋은 2개뿐이며, 이를 별도 PR로 정리해야 합니다.

| 커밋 | 작성자 | 내용 | 처리 |
|------|--------|------|------|
| `634d151d` | delta115zx | feat: 마크다운 테이블 렌더링 | **유지** |
| `cb7732b7` | delta115zx | feat: 지도이동 폴백·차트팝업 등 | **유지** |
| `634d57aa` | ProfessionalSeaweedDevourer | fix: 로그 뷰어 색상 | 제거 |
| `1267c9e7` | ProfessionalSeaweedDevourer | feat: 개인정보 라우팅 | 제거 |
| `72cb4f9b` | ProfessionalSeaweedDevourer | fix: variable_extractor | 제거 |
| `09680f01` | ProfessionalSeaweedDevourer | fix: DB 연결 풀 | 제거 |
| `f73a0cab` | ProfessionalSeaweedDevourer | fix: matplotlib Lock | 제거 |

---

## 실행 절차

### 1단계 — PR #129 닫기

GitHub에서 PR #129를 **Close pull request** (머지하지 않고 닫기).

---

### 2단계 — CHOI2 브랜치를 main 기준으로 재구성

```bash
# CHOI2 브랜치로 이동
git checkout CHOI2
git fetch origin

# main 최신 상태 확인
git log origin/main --oneline -3
```

---

### 3단계 — 새 작업 브랜치 생성 (main 기반)

```bash
git checkout -b CHOI2-clean origin/main
```

---

### 4단계 — 본인 커밋 2개만 cherry-pick

```bash
git cherry-pick 634d151d4b82431ab04bf21f10af619c8945ac76
git cherry-pick cb7732b712bcfdddc0989a45d043a1c7ef05f85c
```

충돌 발생 시:
```bash
# 충돌 파일 수정 후
git add <충돌파일>
git cherry-pick --continue
```

---

### 5단계 — 커밋 내역 확인

```bash
git log origin/main..HEAD --oneline
```

아래 2개만 표시되어야 합니다:
```
cb7732b7 feat: 지도이동 폴백·로딩진행표시·차트팝업·하이라이트hover버그·기본분기 수정
634d151d feat: 마크다운 테이블 렌더링 추가 — 유사 상권 추천 및 다중 상권 비교 표 정상 출력
```

---

### 6단계 — push 및 새 PR 생성

```bash
git push origin CHOI2-clean
```

GitHub에서 `CHOI2-clean → main` PR 생성.
제목 예시: `feat: 마크다운 테이블 렌더링 및 지도 기능 개선`

---

## 참고: 혼입된 5개 커밋이 다루는 파일

PARK 브랜치에서 같은 내용으로 처리 예정인 파일들이므로 cherry-pick 대상에서 제외:

- `integrated_PARK/agents/chat_agent.py`
- `integrated_PARK/domain_router.py`
- `integrated_PARK/kernel_setup.py`
- `integrated_PARK/session_store.py`
- `integrated_PARK/variable_extractor.py`
- `frontend/src/components/LogTable.jsx` (색상 부분만)
- `frontend/src/components/ResponseCard.jsx` (색상 부분만)

delta115zx 본인 커밋이 다루는 파일 (cherry-pick 후 포함되어야 할 파일):

- `frontend/package.json`, `package-lock.json` (remark-gfm)
- `frontend/src/components/LogTable.jsx`, `ResponseCard.jsx` (remarkGfm 적용)
- `frontend/src/components/map/ChatPanel.css`, `ChatPanel.jsx`
- `frontend/src/index.css`
- `frontend/src/components/map/MapView.jsx`
- `frontend/src/pages/UserChat.jsx`
- `integrated_PARK/agents/location_agent.py` (기본 분기 변경)
- `integrated_PARK/db/repository.py` (기본 분기 변경)
- `integrated_PARK/plugins/location_plugin.py` (기본 분기 변경)
