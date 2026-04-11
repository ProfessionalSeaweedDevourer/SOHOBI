이전 세션의 인수인계를 받아 컨텍스트를 복원하라.

CLAUDE.md §다음 세션 부트스트랩 절차를 따른다:

1. `docs/session-reports/`에서 최신 handoff 파일을 특정한다 (ls -t로 정렬)
2. 해당 파일에서 `CLAUDE_HANDOFF_START` ~ `CLAUDE_HANDOFF_END` 블록만 읽는다
   - 인간용 산문 부분은 컨텍스트 복원 목적으로 전체 읽기 금지
3. 블록의 `branch`/`pr` 필드로 현재 상태를 확인한다:
   - `git log --oneline -5 <branch>` (브랜치가 존재하면)
   - `gh pr view <pr번호>` (PR이 있으면)
4. `prev` 필드가 있으면 이전 문서의 블록도 참조한다 (lazy loading)
5. 복원 결과를 보고한다:
   - 현재 브랜치/PR 상태
   - 미해결 이슈 (unresolved)
   - 다음 작업 (next)
   - 주의사항 (traps)
6. "컨텍스트 복원 완료 — 다음 작업을 시작하겠습니까?" 로 확인
