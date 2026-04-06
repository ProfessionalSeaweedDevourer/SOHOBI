# CLAUDE.md & Memory 효율화 계획 (완료 + 추가 변경)

## Context

세션이 쌓이면서 작업 규칙이 CLAUDE.md와 Memory에 분산·중복 저장됨.
추가로, 외부 CLAUDE.md 모범 사례(200줄 이하, 공통 지식 제거, 프로젝트 특화 정보 집중)를 반영하여
CLAUDE.md를 재구성하고, 컨텍스트 50% 도달 시 자동 인수인계 워크플로우를 추가한다.

---

## 변경 파일 목록

| 파일 | 작업 |
|------|------|
| `CLAUDE.md` | 재구성 — 공통지식 제거, 섹션 정리, 신규 규칙 추가 |
| `docs/guides/backend-logs.md` | 신규 — 로그 상세 명령 분리 |
| `~/.claude/.../memory/feedback_pr_attribution.md` | 삭제 (CLAUDE.md 중복) |
| `~/.claude/.../memory/feedback_docs_location.md` | 삭제 (CLAUDE.md 중복) |
| `~/.claude/.../memory/MEMORY.md` | 인덱스 업데이트 |

---

## 1. CLAUDE.md 재구성

### 제거할 항목 (공통 지식 또는 코드 검색으로 알 수 있음)

| 현재 내용 | 제거 이유 |
|-----------|-----------|
| "Python: 3.12 기준, .venv/ 가상환경 사용" | 빌드 명령에서 `.venv/bin/python3`으로 이미 명시됨 |
| "FastAPI + Semantic Kernel + Azure AI Foundry" | `requirements.txt` 검색으로 알 수 있음 |
| "React + Vite + Tailwind CSS" | `package.json` 검색으로 알 수 있음 |
| `scripts/outdated/pull_logs_railway.py` 참고 줄 | 구버전, 사용 안 함 |
| 로그 시간대 필터링 Python 스니펫 (인라인) | → `docs/guides/backend-logs.md`로 이동 |
| `CHANG/`, `CHOI/` 등 팀원 폴더 설명 | 디렉토리 목록으로 알 수 있음 |

### 유지·정리할 항목 (프로젝트 특화 정보)

- `.venv/bin/python3` 빌드 명령 (시스템 Python과 충돌 방지용)
- 에이전트 코드 수정 위치: `integrated_PARK/agents/`만
- 플랜 문서 규칙: `docs/plans/YYYY-MM-DD-이름.md`
- PR 규칙: attribution 금지, 커밋 메시지 형식, 머지 전 검증 필수
- 백엔드 로그 엔드포인트 요약 (1-2줄) + `docs/guides/backend-logs.md` 참조
- `commercial.db` git 포함 경고, `.env` 커밋 금지

### 추가할 섹션 A: 세션 인수인계

컨텍스트 창이 **약 50% 이상** 사용되면 (대화가 매우 길어지거나 압축이 임박한 시점),
Claude는 자동으로:

1. 사용자에게 알린다: `"⚠️ 컨텍스트 50% 초과 — 인수인계 문서를 생성합니다."`
2. `docs/session-reports/YYYY-MM-DD-handoff.md`를 생성한다:
   - 현재 브랜치명
   - 수정된 파일 목록 (git status/diff 기준)
   - 현재 발생 중인 에러 또는 미완료 작업
   - 다음 세션 인수 요약 (3–5줄)
3. 새 세션은 해당 파일을 읽어 맥락을 복원한다.

> 기존 "컴팩션 시 보존할 것" 섹션을 이 규칙으로 대체한다.

### 추가할 섹션 B: Memory 저장 기준

| 저장 위치 | 저장 대상 |
|-----------|----------|
| `CLAUDE.md` | 팀 전체 영구 규칙, 빌드·실행 명령, 아키텍처 결정 |
| `~/.claude/.../memory/` | CLAUDE.md에 없는 개인 피드백, 프로젝트 일시 상태 |

- CLAUDE.md에 이미 있는 규칙은 Memory에 중복 저장하지 않는다.
- 새 패턴 발견 시 Memory에 먼저 저장 → 세션 3회 이상 반복되면 CLAUDE.md로 이전.

### 추가할 섹션 C: 반복 실수 패턴 (향후 업데이트)

초기값은 비어 있으나, 향후 반복 발견된 패턴을 기록.

### PR / 커밋 규칙 보완

기존 내용에 다음을 추가:

- 코드 수정·작성·테스트가 끝나고 **정상 동작이 확인**되면, Claude가 스스로 커밋하고 main 머지용 PR을 연다.
- 작업 브랜치는 **항상 `PARK`** 브랜치를 사용한다. 타 PR의 문제를 해결하는 특수한 경우에만 예외.

---

## 2. 신규 파일: docs/guides/backend-logs.md

현재 CLAUDE.md의 로그 섹션(20줄 이상)을 이 파일로 이동:
- `source integrated_PARK/.env` 후 curl 명령
- 시간대 필터링 Python 스니펫
- `scripts/pull_logs.py` 경로 참조

CLAUDE.md에는 1-2줄 요약 + 참조 경로만 남긴다:
```
백엔드 로그: `$BACKEND_HOST/api/v1/logs?type=queries&limit=50` (BACKEND_HOST는 .env 참조)
상세 명령: docs/guides/backend-logs.md
```

---

## 3. Memory 파일 정리

### 삭제
- `feedback_pr_attribution.md` → CLAUDE.md "PR/커밋 규칙"에 명시됨
- `feedback_docs_location.md` → CLAUDE.md "플랜 문서 규칙"에 명시됨

### 유지
- `project_chart_integration.md` → 프로젝트 상태 (CLAUDE.md에 없는 내용)

### MEMORY.md 업데이트
삭제된 항목 제거 후 Memory 저장 기준 간략 메모 추가.

---

## 예상 결과

| 항목 | 현재 | 변경 후 |
|------|------|---------|
| CLAUDE.md 줄 수 | 107줄 | ~75줄 |
| Memory 파일 수 | 3개 | 1개 |
| 중복 규칙 | 2개 (PR attribution, docs 위치) | 0개 |
| 인수인계 자동화 | 없음 | 컨텍스트 50% 시 자동 |

---

## 검증 방법

1. 새 세션 시작 후 CLAUDE.md 규칙이 올바르게 적용되는지 curl 테스트로 확인
2. 긴 대화 세션에서 Claude가 `docs/session-reports/` 인수인계 파일을 생성하는지 확인
3. `docs/guides/backend-logs.md`의 curl 명령이 실제 Azure 로그를 반환하는지 확인
