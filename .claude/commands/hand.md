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
4. **이전 handoff 의 `[unresolved]` 각 항목을 재판정한다** (복붙 금지):
   - **resolved** — 이번 세션 또는 과거 증거로 해결됨 → 새 handoff `[decisions]` 에 `CLOSED: <item> — <근거>` 한 줄로 이동, `[unresolved]` 에서 제외
   - **invalidated** — 전제가 무너져 더 이상 이슈 아님 → `[decisions]` 에 `INVALIDATED: <item> — <사유>` 한 줄로 이동
   - **carried** — 여전히 유효 → `[unresolved]` 에 유지하되 이월 횟수 주석 (예: `HIGH (carry:3) <항목>`). carry 가 3 이상이면 closure 가능성을 반드시 검토하고 산문에 판정 근거를 기재
   - 기본값으로 그대로 복붙하지 말 것
5. 문서 끝에 `CLAUDE_HANDOFF_START/END` 블록을 추가한다:
   - unresolved: 미해결 이슈 (HIGH/MED/LOW). carry:N 주석 포함
   - decisions: 코드에서 추론 비용 높은 설계 판단 + 이번 세션에서 CLOSED/INVALIDATED 처리한 항목
   - next: 다음 작업 (의존 순서)
   - traps: 시도했으나 실패한 것, 회귀 위험
6. 블록에 git 복구 가능 정보(SHA, 파일 목록)가 포함되지 않았는지 확인
7. 사용자에게 생성 완료를 보고한다
