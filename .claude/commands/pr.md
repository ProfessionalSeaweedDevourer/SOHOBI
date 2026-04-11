현재 브랜치의 변경사항을 커밋하고 PR을 생성하라.

인자: $ARGUMENTS (PR 제목 키워드. 비어 있으면 커밋 내용에서 자동 추론)

## 절차

1. 현재 상태 파악:
   - `git status`로 변경 파일 확인
   - `git diff`로 변경 내용 확인
   - `git log --oneline origin/main..HEAD`로 이미 커밋된 내용 확인
2. 미커밋 변경이 있으면 CLAUDE.md 커밋 규칙에 따라 커밋한다:
   - 메시지 형식: `type: 한국어 설명`
3. `git push origin <현재브랜치>`
4. `gh pr list --head <브랜치> --state open`으로 열린 PR 확인:
   - 열린 PR이 있으면 해당 PR 번호를 보고한다
   - 없으면 `gh pr create`로 새 PR을 생성한다:
     - Test Plan 체크박스 포함
     - CLAUDE.md PR body 형식 준수
5. PR 생성 직후 `/tc` 절차에 따라 TC를 실행한다
6. PR 번호를 사용자에게 보고한다
