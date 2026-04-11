PR #$ARGUMENTS 를 리뷰하라.

**인자**: `$ARGUMENTS` — 첫 번째 공백 구분 토큰을 PR 번호로 사용한다. 나머지는 컨텍스트 메모로 무시한다.

1. `gh pr view <PR번호>`로 PR 정보(제목, 본문, 변경 파일) 확인
2. `gh pr diff <PR번호>`로 전체 diff 확인
3. 변경된 소스 파일을 읽고 다음을 점검:
   - 코드 품질, 버그, 보안 취약점
   - DOMAIN=localhost 회귀 여부 (grep 필수)
   - .env 파일 커밋 여부
   - CLAUDE.md의 프로젝트 규칙 준수 여부
4. 실행 가능한 테스트가 있으면 실행
5. 리뷰 결과를 PR에 코멘트로 남긴다 (`gh pr comment <PR번호>`)
