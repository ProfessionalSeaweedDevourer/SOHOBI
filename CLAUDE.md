# SOHOBI 프로젝트 — Claude 영구 지시

## 빌드 & 실행

```bash
# 백엔드
cd integrated_PARK && .venv/bin/python3 api_server.py

# 프론트엔드
cd frontend && npm run dev

# 의존성 설치
cd integrated_PARK && .venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

## 테스트

공식 테스트 스위트 없음. API 동작 확인:

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트 질문"}'
```

## 핵심 디렉토리

| 경로 | 설명 |
|------|------|
| `integrated_PARK/` | 메인 통합 버전 — 실제 작동 코드 |
| `integrated_PARK/agents/` | 하위 에이전트 (법률·세무, 상권, 재무 등) |
| `integrated_PARK/api_server.py` | FastAPI 진입점 |
| `integrated_PARK/orchestrator.py` | Semantic Kernel 오케스트레이션 |
| `integrated_PARK/signoff/` | 최종 검증 에이전트 |
| `integrated_PARK/db/` | DB DAO 모듈 — 실제 DB는 Azure 백엔드에 위치 (SQLite 로컬 파일 없음) |
| `frontend/` | React + Vite + Tailwind 프론트엔드 |
| `docs/plans/` | 플랜 문서 (`YYYY-MM-DD-이름.md`) |
| `docs/session-reports/` | 세션 리포트 및 인수인계 문서 |

## 프로젝트 규칙

- 에이전트 코드는 `integrated_PARK/agents/`에서만 수정
- 의존성: `requirements.txt`에 `==` 버전 고정
- 플랜 문서: **반드시 `docs/plans/YYYY-MM-DD-이름.md`** 형식으로 저장 (Claude Code 내부 플랜과 동시에)

## PR / 커밋 규칙

- 커밋 메시지: `type: 한국어 설명` (예: `fix: location 에이전트 버그 수정`)
- 커밋 메시지와 PR 본문에 "Generated with Claude Code" 또는 "Co-Authored-By: Claude" attribution 포함 금지
- 작업 브랜치는 `팀원브랜치-작업명` 패턴으로 **반드시 `origin/main` 기반으로 신규 생성**한다:

  | GitHub 계정 | 네임스페이스 브랜치 | 작업 브랜치 예시 |
  | ----------- | ------------------ | ---------------- |
  | ProfessionalSeaweedDevourer | `PARK` | `PARK-fix-login` |
  | zSob2048 | `CHANG` | `CHANG-refactor-agent` |
  | delta115zx | `CHOI2` | `CHOI2-add-chart` |
  | dannynam13 | `NAM` | `NAM-update-docs` |
  | TerryBlackhoodWoo | `WOO-clean2` | `WOO-clean2-map-fix` |

  네임스페이스 브랜치(`PARK` 등)는 영구 보존하되 **직접 커밋하지 않는다**.  
  > **주의**: git ref 제약으로 `PARK/작업명`(슬래시) 패턴은 사용 불가. 반드시 대시(`PARK-작업명`) 사용.

- 코드 수정·테스트 완료 후 정상 동작이 확인되면 Claude가 **스스로 커밋하고 main 머지용 PR**을 연다
- PR 머지 지시는 검증 완료 후에만. 검증 전 추가 수정은 같은 브랜치에 커밋을 추가
- `gh pr merge` 시 팀원 네임스페이스 브랜치(`PARK`, `CHANG` 등)와 장기 작업 브랜치는 **`--delete-branch` 사용 금지** — 영구 작업 공간으로 유지해야 함
- 단, 특정 업데이트 작업 및 PR을 위해 생성한 **임시 브랜치**는 머지 후 삭제 허용
- **PR 생성 직후** Test Plan의 각 TC를 직접 실행하고 결과를 보고한다 (아래 테스트 실행 루틴 참조)
- **push 후 반드시** `gh pr list --head <브랜치> --state open` 으로 열린 PR을 확인한다:
  - 열린 PR이 있으면 해당 PR 번호를 사용자에게 알린다
  - 없으면 (머지·닫힘·미생성) 즉시 새 PR을 열고 번호를 알린다
  - "PR에 반영되었습니다"는 확인 없이 절대 말하지 않는다

## 브랜치 워크플로우

이 프로젝트는 **squash merge**를 사용한다. 장기 브랜치에 쌓인 squash-merge 커밋들은 다음 rebase 시 `patch contents already upstream` 충돌을 반복 유발하며, 멀티 세션 환경에서 `git reset --hard` 리셋은 다른 세션의 미커밋 변경을 파괴할 수 있다. 이를 방지하기 위해 **PR마다 `origin/main` 기반 fresh 브랜치**를 사용한다.

### PR 시작 절차

```bash
# 1. 최신 main 가져오기
git fetch origin

# 2. main 기반 작업 브랜치 생성 (슬래시 불가 → 대시 사용)
git checkout -b PARK-<작업명> origin/main

# 3. 작업 및 커밋
```

### PR 생성 전 절차

```bash
# rebase (main 기반이므로 --skip 불필요)
git rebase origin/main
git push origin PARK-<작업명>

# PR 커밋 범위 확인
git log --oneline origin/main..HEAD
```

### PR당 커밋 수 원칙

- PR 하나에 **관련 커밋만** 포함되어야 한다
- 관련 없는 커밋이 보이면 `git rebase --onto origin/main <base-commit> <브랜치>` 로 정리 후 PR 생성

## 워크트리 병렬 운용

여러 브랜치를 동시에 작업해야 할 때 **git worktree**를 사용한다. 각 워크트리는 물리적으로 별도 디렉토리이므로 독립된 Claude Code 세션(또는 VS Code 창)에서 병렬 작업이 가능하다.

### 언제 사용하는가

- PR 리뷰 중 다른 브랜치에서 신규 작업을 병행할 때
- 라이브 서버 장애 시 현재 작업을 중단하지 않고 핫픽스할 때
- 여러 PR의 코드를 동시에 비교·수정할 때

### 워크트리 생성

```bash
# 자동 스크립트 (환경 초기화 포함)
./scripts/worktree-setup.sh PARK-fix-login           # origin/main 기반 새 브랜치
./scripts/worktree-setup.sh PARK-review-231 pr-branch # 기존 브랜치 체크아웃
```

스크립트가 수행하는 것:

1. `git worktree add` — 워크트리 생성
2. `.env` 파일 복사 (backend / frontend)
3. `npm install` (frontend)
4. `python3 -m venv` + `pip install` (backend)

생성 위치: `../SOHOBI-<브랜치명>/`

### 수동 생성 (스크립트 없이)

```bash
git fetch origin
git worktree add ../SOHOBI-<브랜치명> -b <브랜치명> origin/main
cp integrated_PARK/.env ../SOHOBI-<브랜치명>/integrated_PARK/.env
cd ../SOHOBI-<브랜치명>/frontend && npm install
```

### 제약 사항

| 항목 | 설명 |
| ------ | ------ |
| 같은 브랜치 불가 | 두 워크트리가 동일 브랜치를 체크아웃할 수 없음 (git 제약) |
| `.env` 별도 복사 | `.gitignore`된 파일은 워크트리 간 공유되지 않음 |
| `node_modules` 별도 설치 | 각 워크트리에서 `npm install` 필요 |
| `.git`은 공유 | reflog, stash, 브랜치 목록은 모든 워크트리가 동일한 `.git` 참조 |
| 동시 rebase 주의 | 두 세션이 동시에 같은 원격 브랜치를 rebase하면 lock 충돌 가능 |

### 정리

```bash
# 워크트리 제거
git worktree remove ../SOHOBI-<브랜치명>

# 현황 확인
git worktree list
```

워크트리 디렉토리는 PR 머지 후 정리한다. 네임스페이스 브랜치(`PARK` 등)에 연결된 워크트리는 유지해도 무방하다.

## PR 생성 후 테스트 실행 루틴

PR을 연 직후 Test Plan의 각 TC를 직접 실행하고 결과를 사용자에게 보고한다.

### 테스트 유형별 도구

| 테스트 유형 | 도구 | 실행 조건 |
| ----------- | ---- | --------- |
| API E2E | `curl` + `$BACKEND_HOST` (`.env` 로드) | 항상 실행 |
| 백엔드 로그 확인 | `GET $BACKEND_HOST/api/v1/logs` | API 테스트 후 |
| DB / 플러그인 단위 | `pytest` (`.venv`) | 관련 파일 수정 시 |
| 프론트엔드 UI | playwright MCP (`browser_navigate` → `browser_snapshot`) | UI 변경 시 |

### 실행 절차

1. `source integrated_PARK/.env` 로 환경변수 로드
2. TC 번호 순서대로 각 테스트 실행
3. 각 TC마다 `✅ PASS` / `❌ FAIL` 결과 출력
4. FAIL 발생 시 — 즉시 수정 후 동일 브랜치에 커밋 → 재테스트
5. 전체 PASS 확인 후 "테스트 완료 — PR #번호 머지 가능" 보고

### 실행 불가 예외

- 로컬 서버 미기동 상태의 localhost 테스트 → 사용자에게 기동 요청
- Azure Container Apps cold start → 30초 대기 후 1회 재시도

## 세션 인수인계

다음 중 하나라도 해당되면 즉시 인수인계 문서를 생성한다:

- 대화 턴이 20회를 초과한 경우
- 에러 해결 없이 동일 문제를 3회 이상 반복한 경우
- 작업 범위가 최초 요청에서 3개 이상의 파일로 확장된 경우

### 인수인계 문서 구조

인수인계 문서는 **인간용 산문**과 **Claude용 압축 블록** 두 부분으로 구성한다.

파일 경로: `docs/session-reports/YYYY-MM-DD-<이름>-handoff.md`

```markdown
# 세션 인수인계 제목

(인간용 산문: 브랜치, 커밋 목록, 수정 파일 테이블, 상세 설명 등 자유 형식)

---
<!-- CLAUDE_HANDOFF_START
branch: <작업 브랜치명>
pr: <PR 번호 또는 none>
prev: <이전 인수인계 파일명 또는 none>

[unresolved]
- <HIGH|MED|LOW> <파일:라인> <문제 1줄> <해결 방향 1줄>

[decisions]
- <코드에서 추론 비용 높은 설계 판단. 1줄>

[next]
<번호 → 작업. 의존 순서대로>

[traps]
- <시도했으나 실패한 것, 회귀 위험 등>
CLAUDE_HANDOFF_END -->
```

#### 블록 작성 규칙

- **git에서 복구 가능한 정보를 블록에 쓰지 않는다**: 커밋 목록/SHA, 수정 파일 테이블, PR 상태 — 이것들은 인간용 산문에만 기재
- 4섹션(unresolved/decisions/next/traps) 중 해당 없는 섹션은 생략 가능
- 각 항목은 1-2줄 이내. 맥락 압축 우선

### 인수인계 문서 생성 절차

1. 사용자에게 알린다: `"⚠️ 인수인계 트리거 발동 — 인수인계 문서를 생성합니다."`
2. `docs/session-reports/YYYY-MM-DD-<이름>-handoff.md`를 생성한다
3. 인간용 산문 작성 (브랜치명, 수정 파일 목록, 에러·미완료 작업, 다음 세션 인수 요약 3-5줄)
4. 문서 끝에 `CLAUDE_HANDOFF_START/END` 블록 필수 추가
5. 블록에 git 복구 가능 정보가 포함되지 않았는지 확인

### 다음 세션 부트스트랩 절차

새 세션이 인수인계를 받을 때 다음 순서로 컨텍스트를 복원한다:

1. `docs/session-reports/`에서 최신 handoff 파일 특정 (`ls -t`)
2. **`CLAUDE_HANDOFF_START` 블록만 읽는다** — 인간용 산문 부분은 컨텍스트 복원 목적으로 전체 읽기 금지
3. `branch`/`pr` 필드로 `git log`, `gh pr view` 실행하여 현재 상태 확인
4. `prev` 필드가 있으면 필요 시 이전 문서의 블록도 참조 (lazy loading)

## Memory 저장 기준

| 저장 위치 | 저장 대상 |
| --------- | -------- |
| `CLAUDE.md` | 팀 전체 영구 규칙, 빌드·실행 명령, 아키텍처 결정 |
| `~/.claude/.../memory/` | CLAUDE.md에 없는 개인 피드백, 프로젝트 일시 상태 |

- CLAUDE.md에 이미 있는 규칙은 Memory에 중복 저장하지 않는다
- 새 패턴을 Memory에 먼저 저장 → 세션 3회 이상 반복 시 CLAUDE.md로 이전

## 백엔드 로그

배포: Azure Container Apps. `integrated_PARK/.env`의 `BACKEND_HOST` 참조.

```bash
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -m json.tool
```

상세 명령 및 필터링: [`docs/guides/backend-logs.md`](docs/guides/backend-logs.md)

## 도메인 & 인프라

- 프론트엔드 도메인: `sohobi.net` (Azure DNS zone: `.env` 참조)
- 백엔드: Azure Container Apps (`BACKEND_HOST` in `.env`)
- SEO canonical URL, sitemap, OG 태그 등에서 도메인은 **`sohobi.net`** 사용

## 주의 사항

- `.env` 파일에는 Azure API 키가 있음 — 절대 커밋하지 말 것
- `integrated_PARK/.venv/`는 gitignore됨

## 반복 실수 패턴

<!-- Claude가 반복적으로 틀린 사항을 여기에 기록. 주기적으로 업데이트. -->
