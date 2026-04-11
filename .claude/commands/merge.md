PR #$ARGUMENTS 를 admin squash merge하고 후속 검증을 수행하라.

1. `gh pr view $ARGUMENTS --json state,mergeable,title`로 PR 상태 확인
2. mergeable이 아니면 원인을 보고하고 중단
3. `gh pr merge $ARGUMENTS --admin --squash`로 머지 실행
4. 머지 완료 후:
   - `git checkout main && git pull origin main`
   - PR의 Test Plan TC를 재실행한다 (CLAUDE.md §테스트 실행 루틴)
   - 결과를 PR에 코멘트로 남긴다: `gh pr comment $ARGUMENTS --body "..."`
5. TC FAIL 시:
   - 핫픽스 브랜치를 즉시 생성한다: `git checkout -b fix/park-hotfix-$ARGUMENTS origin/main`
   - 수정 후 새 PR을 연다
6. TC 전체 PASS 시 "머지 완료 — TC 전체 PASS" 보고
