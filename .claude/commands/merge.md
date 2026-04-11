PR #$ARGUMENTS 를 admin squash merge하고 후속 검증을 수행하라.

**인자**: `$ARGUMENTS` — 첫 번째 공백 구분 토큰을 PR 번호로 사용한다. 나머지는 컨텍스트 메모로 무시한다.

1. `gh pr view <PR번호> --json state,mergeable,title`로 PR 상태 확인
2. mergeable이 아니면 원인을 보고하고 중단
3. `gh pr merge <PR번호> --admin --squash`로 머지 실행
4. 머지 완료 후:
   - `git checkout main && git pull origin main`
   - PR의 Test Plan TC를 재실행한다 (CLAUDE.md §테스트 실행 루틴)
   - 결과를 PR에 코멘트로 남긴다: `gh pr comment <PR번호> --body "..."`
5. TC FAIL 시:
   - `git config user.email`로 현재 커미터를 확인하고 CLAUDE.md author 매핑 테이블에서 author를 조회한다
   - 핫픽스 브랜치를 즉시 생성한다: `git checkout -b fix/<author>-hotfix-<PR번호> origin/main`
   - 수정 후 새 PR을 연다
6. TC 전체 PASS 시 "머지 완료 — TC 전체 PASS" 보고
