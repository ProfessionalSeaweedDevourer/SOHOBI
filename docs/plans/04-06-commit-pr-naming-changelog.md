# PR 네이밍 전수 정규화 + Changelog 개선

## Context

전체 155개 PR 중 43개(MERGED 36, CLOSED 7)가 `type: 한국어 설명` 표준을 따르지 않는다.
PR 제목은 merged·closed 상태에서도 `gh pr edit --title` 으로 수정 가능하다.
커밋 메시지는 main 히스토리 재작성이 필요해 제외한다.
Changelog.jsx는 GitHub Commits API를 직접 호출하므로, Merge commit이 "기타" 배지로 잡음 노출되는 구조적 문제도 함께 수정한다.

---

## 1단계 — PR 제목 전수 수정 (43건)

### Phase A — 최근 6건 (우선)

| PR | 현재 제목 | 수정 제목 |
|----|-----------|-----------|
| #154 | `Choi2` | `fix: 상권분석 데이터 기준 연도 2024 Q4 → 2025 Q4 전체 반영` |
| #151 | `feat/fix: 리포트 스펙 완성 + 보안 취약점 수정` | `feat: 리포트 스펙 완성 및 보안 취약점 수정` |
| #133 | `Choi2 clean` | `feat: 마크다운 테이블 렌더링 및 지도 UX 개선 (CHOI2 정리본)` |
| #130 | `DB 연결/해제 공통 메소드 추가 및 refactoring/Docstring 추가` | `refactor: DB 연결/해제 공통 메소드 분리 및 Docstring 추가` |
| #38 | `fix/perf: Container Apps signoff 수정 및 응답 속도 개선` | `fix: Container Apps signoff 수정 및 응답 속도 개선` |
| #23 | `PARK → main: 버그 수정, Location 에이전트 통합, 아키텍처 문서` | `feat: 버그 수정, Location 에이전트 통합 및 아키텍처 문서 추가` |

### Phase B — MERGED 나머지 (30건)

| PR | 현재 제목 | 수정 제목 |
|----|-----------|-----------|
| #114 | `점포수 미확인시 fallback처리 수정` | `fix: 점포수 미확인 시 fallback 처리 수정` |
| #105 | `SOHOBI_MAP 백엔드 구현` | `feat: SOHOBI_MAP 백엔드 DAO 및 컨트롤러 구현` |
| #102 | `로직 방어 및 fallback처리` | `fix: 로직 방어 및 fallback 처리 추가` |
| #96 | `DB 관련 수정 및 내부 지역/업종 추출 추가` | `feat: DB 관련 수정 및 내부 지역/업종 추출 추가` |
| #86 | `SOHOBI 맵 UI 개선` | `feat: SOHOBI 맵 UI 최신본 통합 및 개선` |
| #85 | `#79 변수 활용 및 DB활성화` | `feat: 변수 활용 및 DB 활성화` |
| #84 | `Choi2` | `feat: 법령 에이전트 수정·상권분석 기준 오류 수정·행정 에이전트 KB 플러그인 추가` |
| #77 | `NAM2: 정부지원사업 맞춤 추천 엔진 + 데이터 파이프라인` | `feat: 정부지원사업 맞춤 추천 엔진 및 Azure Functions 데이터 파이프라인 추가` |
| #75 | `초기값 출력 확인 및 프롬프트 중복 정돈` | `refactor: 초기값 출력 확인 및 프롬프트 중복 정돈` |
| #72 | `상권분석 에이전트 시각화 도표 표기 수정` | `fix: 상권분석 에이전트 시각화 도표 표기 수정` |
| #67 | `PR #65 코멘트 반영` | `fix: 차트 툴팁 코멘트 반영` |
| #66 | `Choi2` | `feat: 상권분석 시각화 개선 및 행정 에이전트 KB 플러그인 추가` |
| #65 | `차트 호버시 나오는 툴팁 수정` | `fix: 차트 호버 시 툴팁 수정` |
| #60 | `SOHOBI MAP 통합 가이드 포함 (README_SOHOBI_MAP.md참고요망)` | `docs: SOHOBI MAP 통합 가이드 및 랜드마크 보강 추가` |
| #56 | `Choi2` | `chore: 지도 업데이트 및 병합 준비 (2026-03-30)` |
| #52 | `상권분석 에이전트 + 지도 관련 개선` | `feat: 상권분석 에이전트 및 지도 관련 개선` |
| #51 | `0326 지역/업종관련 연동 추가(코드기반으로 변경)` | `feat: 지역/업종 코드 기반 연동 추가` |
| #44 | `SOHOBI 지도 공유의건(260325)` | `chore: SOHOBI 지도 백엔드 컨트롤러 IP 변경 (2026-03-25)` |
| #43 | `Choi` | `perf: 상권분석 에이전트 응답 속도 개선 및 토큰 절약` |
| #34 | `Choi` | `fix: 상권분석 에이전트 데이터 없음 처리 및 법률 RAG 개선` |
| #28 | `stateless 구상 테스트` | `test: stateless 구상 테스트` |
| #22 | `GovSupportPlugin 정부지원사업 RAG 검색 추가` | `feat: GovSupportPlugin 정부지원사업 RAG 검색 추가` |
| #21 | `Choi` | `feat: 법률 RAG 데이터 추가 및 수정` |
| #19 | `Choi` | `chore: README.md 수정 및 .env 전환 테스트` |
| #16 | `DB버전 점포데이터 추가` | `feat: DB버전 점포데이터 추가` |
| #15 | `DB: commercial.db 2024년 4분기 단일 분기로 축소 (54MB → 13MB) 및 Git 포함` | `chore: commercial.db 2024 Q4 단일 분기로 축소 (54MB → 13MB)` |
| #14 | `DB버전 의존성, README.md수정` | `chore: DB버전 의존성 및 README.md 수정` |
| #13 | `PARK: LocationAgent 이식 + 재무 시뮬레이션 정리 (tax_rate·신뢰구간 제거)` | `feat: LocationAgent 이식 및 재무 시뮬레이션 정리` |
| #12 | `상권분석 에이전트 DB버전 추가` | `feat: 상권분석 에이전트 DB버전 추가` |
| #11 | `통합: LocationAgent (상권분석) 이식 및 Sign-off 루프 연결` | `feat: LocationAgent 이식 및 Sign-off 루프 연결` |
| #9 | `상권 에이전트: 모델 변경 및 프롬프트 개선` | `refactor: 상권 에이전트 모델 변경 및 프롬프트 개선` |
| #8 | `재무 에이전트: 손실 확률 중심 응답·루브릭 재구성` | `refactor: 재무 에이전트 손실 확률 중심 응답·루브릭 재구성` |
| #7 | `백엔드: Path B 세션 재무 변수 추출` | `feat: 백엔드 Path B 세션 재무 변수 추출` |

### Phase C — CLOSED 7건 (선택)

| PR | 현재 제목 | 수정 제목 |
|----|-----------|-----------|
| #73 | `SOHOBI 지도 프론트 통합` | `feat: SOHOBI 지도 프론트 통합` |
| #61 | `0330 차트 front출력으로 변경` | `feat: 차트 프론트 출력 방식으로 변경` |
| #45 | `0325 state 누적+chart 출력 관련 통합본` | `feat: state 누적 및 차트 출력 통합` |
| #20 | `0317) DB연동함수 추가` | `feat: DB 연동 함수 추가` |
| #10 | `0316일자` | `chore: 초기 세팅 (2026-03-16)` |
| #1 | `Add files via upload` | `chore: 초기 파일 업로드` |

---

## 2단계 — Changelog.jsx 구조 개선

**파일:** `frontend/src/pages/Changelog.jsx`

### 2-A. Merge 커밋 필터링 (line 169, 188)

`useEffect` load()와 `loadMore()` 에서 raw 배열을 필터링한 뒤 `parseCommit` 적용:

```js
const isNotMerge = (r) =>
  !r.commit.message.startsWith("Merge pull request") &&
  !r.commit.message.startsWith("Merge branch");

// useEffect load() — 현재:
setCommits(data.map(parseCommit));
// 수정:
setCommits(data.filter(isNotMerge).map(parseCommit));

// loadMore() — 현재:
setCommits((prev) => [...prev, ...data.map(parseCommit)]);
// 수정:
setCommits((prev) => [...prev, ...data.filter(isNotMerge).map(parseCommit)]);
```

### 2-B. `debug` 타입 추가 (line 26 부근)

히스토리에 `debug:` 접두사 커밋이 존재하나 TYPE_MAP에 없어 "기타" 표시됨.

```js
debug: { label: "디버그", color: "#a3a3a3" },
```

---

## 수정 파일

- `frontend/src/pages/Changelog.jsx` (Merge 필터링 + debug 타입)
- GitHub PR 제목 43건 (코드 파일 변경 없음, `gh pr edit` 으로 처리)

---

## 실행 방식

Phase A (6건) → Phase B (30건) → Changelog 코드 수정 → Phase C (7건, 선택) 순으로 진행.
각 Phase는 `gh pr edit <N> --title "..."` 명령을 일괄 실행한다.

---

## 검증

1. `gh pr list --state all --limit 200 --json number,title | python3 -c "..."` 로 비규격 PR 수 0 확인
2. `/changelog` 페이지에서 "Merge pull request" 행이 사라졌는지 확인
3. `debug:` 커밋이 "디버그" 배지로 표시되는지 히스토리 스크롤로 확인
