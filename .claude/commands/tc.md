PR #$ARGUMENTS 의 Test Plan에 있는 TC를 실행하라.

**인자**: `$ARGUMENTS` — 첫 번째 공백 구분 토큰을 PR 번호로 사용한다. 나머지는 컨텍스트 메모로 무시한다.

1. `gh pr view <PR번호> --json body`로 PR body를 가져온다
2. body에서 Test Plan 섹션의 체크박스 항목(TC)을 파싱한다
3. `source backend/.env`로 환경변수 로드
4. TC를 번호 순서대로 실행한다:
   - API E2E: `curl` + `$BACKEND_HOST`
   - 백엔드 로그: `GET $BACKEND_HOST/api/v1/logs`
   - pytest: `.venv/bin/pytest` (관련 파일 수정 시)
   - UI: playwright MCP `browser_navigate` → `browser_snapshot` (UI 변경 시)
5. 각 TC마다 `✅ PASS` / `❌ FAIL` 결과를 출력한다
6. FAIL 발생 시 원인 분석 후 수정 → 동일 브랜치에 커밋 → 재테스트
7. 전체 PASS 시 PR body의 체크박스를 업데이트한다: `gh pr edit <PR번호> --body "..."`
8. "테스트 완료 — PR #<PR번호> 머지 가능" 보고

실행 불가 예외:
- 로컬 서버 미기동 상태의 localhost 테스트 → 사용자에게 기동 요청
- Azure Container Apps cold start → 30초 대기 후 1회 재시도
