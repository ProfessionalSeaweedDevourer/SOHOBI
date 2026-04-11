# SOHOBI — Claude Code 활용 가이드

이 프로젝트에서 Claude Code를 효과적으로 사용하기 위한 안내.

## Custom Slash Commands

`.claude/commands/` 에 정의된 프로젝트 전용 단축 명령. Claude Code 입력창에서 `/명령` 으로 호출한다.

### `/prrev <PR번호>`

PR을 리뷰한다. diff 확인, 코드 품질·보안 점검, DOMAIN=localhost 회귀 검사, 실행 가능한 테스트 수행 후 PR에 리뷰 코멘트를 남긴다.

```
/prrev 274
```

### `/pr [제목]`

현재 브랜치의 변경사항을 커밋하고 PR을 생성한다. 이미 열린 PR이 있으면 해당 번호를 보고. 생성 직후 TC를 자동 실행한다.

```
/pr
/pr 의존성 핀 강화
```

### `/tc <PR번호>`

PR의 Test Plan에 있는 TC(테스트 케이스)를 순서대로 실행하고 PASS/FAIL을 보고한다. FAIL 시 즉시 수정 → 재테스트. 전체 PASS 시 PR body 체크박스를 업데이트한다.

```
/tc 274
```

### `/logs [타입 개수]`

백엔드 로그(`$BACKEND_HOST/api/v1/logs`)를 조회하고 요약한다. 인자 없으면 최근 쿼리 50건.

```
/logs              # queries 50건 (기본)
/logs errors 20    # 에러 20건
/logs rejections 100
```

### `/hand [제목]`

세션 인수인계 문서를 즉시 생성한다. `docs/session-reports/YYYY-MM-DD-<제목>-handoff.md` 형식. CLAUDE.md의 인수인계 절차(인간용 산문 + CLAUDE_HANDOFF 블록)를 따른다.

```
/hand
/hand auth-refactor
```

### `/merge <PR번호>`

PR을 `--admin --squash` 머지하고 후속 검증을 수행한다. main pull → TC 재실행 → 결과를 PR에 코멘트. FAIL 시 핫픽스 브랜치를 자동 생성한다.

```
/merge 274
```

### `/tree [브랜치명]`

git worktree를 생성한다. 브랜치명을 생략하면 현재 작업 맥락에서 자동 추론한다. `.env` 복사, `npm install` 등 환경 초기화를 포함한다.

```
/tree feat/park-fix-login
/tree                        # 맥락에서 자동 추론
```

### `/boot`

이전 세션의 인수인계를 받아 컨텍스트를 복원한다. 최신 handoff 파일의 CLAUDE_HANDOFF 블록을 읽고, 브랜치/PR 상태를 확인하여 보고한다.

```
/boot
```

## 프로젝트 구조와 Claude Code의 역할

### CLAUDE.md — 자동화 규칙

`CLAUDE.md`는 Claude가 **자동으로** 따르는 영구 규칙이다:

- 커밋 메시지 형식 (`type: 한국어 설명`)
- 브랜치 명명 규칙 (`<type>/<author>-<작업명>`)
- PR 생성 후 TC 자동 실행
- 머지 후 TC 재실행 및 결과 코멘트
- 인수인계 자동 트리거 (20턴 초과, 3회 반복 에러, 3파일 이상 확장)

### `.claude/commands/` — 수동 단축 명령

사용자가 **명시적으로 호출**하는 명령. CLAUDE.md의 자동 규칙과 겹치지 않도록 설계되어 있다.

### Memory

`~/.claude/.../memory/`에 저장되는 세션 간 기억. CLAUDE.md에 없는 개인 피드백, 프로젝트 임시 상태를 저장한다. CLAUDE.md에 이미 있는 규칙은 중복 저장하지 않는다.

### 워크트리 병렬 운용

여러 브랜치를 동시에 작업할 때 `git worktree`를 사용한다. 각 워크트리는 별도 디렉토리에서 독립된 Claude Code 세션으로 운용한다. `/tree` 명령으로 간편하게 생성할 수 있다.

## 관련 문서

- [CLAUDE.md](../../CLAUDE.md) — 영구 규칙 전체
- [backend-logs.md](backend-logs.md) — 백엔드 로그 상세 필터링
- [code-review.md](code-review.md) — PR 리뷰 체크리스트
