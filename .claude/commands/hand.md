세션 인수인계 문서를 즉시 생성하라.

인자: $ARGUMENTS (인수인계 제목 키워드. 없으면 현재 작업 내용에서 자동 추출)

CLAUDE.md §세션인수인계 절차를 따른다:

1. 현재 브랜치, 열린 PR, 수정 파일 목록을 파악한다
2. `docs/session-reports/YYYY-MM-DD-<키워드>-handoff.md` 파일을 생성한다
3. 인간용 산문을 작성한다:
   - 브랜치명, 커밋 목록 (git log --oneline)
   - 수정 파일 테이블
   - 에러·미완료 작업
   - 다음 세션 인수 요약 3-5줄
4. 문서 끝에 `CLAUDE_HANDOFF_START/END` 블록을 추가한다:
   - unresolved: 미해결 이슈 (HIGH/MED/LOW)
   - decisions: 코드에서 추론 비용 높은 설계 판단
   - next: 다음 작업 (의존 순서)
   - traps: 시도했으나 실패한 것, 회귀 위험
5. 블록에 git 복구 가능 정보(SHA, 파일 목록)가 포함되지 않았는지 확인
6. 사용자에게 생성 완료를 보고한다
