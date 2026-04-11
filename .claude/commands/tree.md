워크트리를 생성하라.

인자: $ARGUMENTS (브랜치명. 비어 있으면 아래 자동 추론 절차를 따른다)

## 브랜치명 자동 추론 (인자 없을 때)

현재 대화 맥락에서 브랜치명을 결정한다:
- 작업 유형(feat/fix/refactor/chore/docs/security 등)과 작업 내용을 파악
- CLAUDE.md 브랜치 명명 규칙에 따라 `<type>/<author>-<작업명>` 형식으로 생성
- 예: 로그인 버그 수정 중이면 → `fix/park-login-bug`
- 사용자에게 추론한 브랜치명을 확인받은 후 진행

## 실행 절차

1. `./scripts/worktree-setup.sh <브랜치명>` 실행
   - 스크립트가 수행하는 것: git worktree add, .env 복사, npm install, venv + pip install
   - 생성 위치: `../SOHOBI-<브랜치명>/`
2. 스크립트가 없거나 실패하면 수동 절차 실행:
   ```
   git fetch origin
   git worktree add ../SOHOBI-<브랜치명> -b <브랜치명> origin/main
   cp integrated_PARK/.env ../SOHOBI-<브랜치명>/integrated_PARK/.env
   cp frontend/.env ../SOHOBI-<브랜치명>/frontend/.env
   cd ../SOHOBI-<브랜치명>/frontend && npm install
   ```
3. 결과를 보고한다:
   - 워크트리 경로
   - 브랜치명
   - 환경 초기화 상태 (.env, node_modules, venv)
4. `git worktree list`로 현재 워크트리 목록을 출력한다
