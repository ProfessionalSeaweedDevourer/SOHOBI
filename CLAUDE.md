# SOHOBI 프로젝트 — Claude 영구 지시

## 빌드 & 실행

```bash
# 백엔드
cd integrated_PARK && .venv/bin/python3 api_server.py

# 프론트엔드
cd frontend && npm run dev

# 의존성 설치
cd integrated_PARK && .venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

## 테스트

공식 테스트 스위트 없음. API 동작 확인:

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트 질문"}'
```

## 핵심 디렉토리

| 경로 | 설명 |
|------|------|
| `integrated_PARK/` | 메인 통합 버전 — 실제 작동 코드 |
| `integrated_PARK/agents/` | 하위 에이전트 (법률·세무, 상권, 재무 등) |
| `integrated_PARK/api_server.py` | FastAPI 진입점 |
| `integrated_PARK/orchestrator.py` | Semantic Kernel 오케스트레이션 |
| `integrated_PARK/signoff/` | 최종 검증 에이전트 |
| `integrated_PARK/db/commercial.db` | 상권 SQLite DB (2024 Q4, 서울) — 13MB, git 포함됨 |
| `frontend/` | React + Vite + Tailwind 프론트엔드 |
| `docs/plans/` | 플랜 문서 (`YYYY-MM-DD-이름.md`) |
| `docs/session-reports/` | 세션 리포트 및 인수인계 문서 |

## 프로젝트 규칙

- 에이전트 코드는 `integrated_PARK/agents/`에서만 수정
- 의존성: `requirements.txt`에 `==` 버전 고정
- 플랜 문서: **반드시 `docs/plans/YYYY-MM-DD-이름.md`** 형식으로 저장 (Claude Code 내부 플랜과 동시에)

## PR / 커밋 규칙

- 커밋 메시지: `type: 한국어 설명` (예: `fix: location 에이전트 버그 수정`)
- 커밋 메시지와 PR 본문에 "Generated with Claude Code" 또는 "Co-Authored-By: Claude" attribution 포함 금지
- 작업 브랜치는 아래 팀원별 브랜치 사용 (타 PR 문제 해결 시 예외):

  | GitHub 계정 | 브랜치 |
  | ----------- | ------ |
  | ProfessionalSeaweedDevourer | `PARK` |
  | zSob2048 | `CHANG` |
  | delta115zx | `CHOI2` |
  | dannynam13 | `NAM` |
  | TerryBlackhoodWoo | `WOO-clean2` |

- 코드 수정·테스트 완료 후 정상 동작이 확인되면 Claude가 **스스로 커밋하고 main 머지용 PR**을 연다
- PR 머지 지시는 검증 완료 후에만. 검증 전 추가 수정은 같은 브랜치에 커밋을 추가
- **PR 생성 직후** Test Plan의 각 TC를 직접 실행하고 결과를 보고한다 (아래 테스트 실행 루틴 참조)
- **push 후 반드시** `gh pr list --head <브랜치> --state open` 으로 열린 PR을 확인한다:
  - 열린 PR이 있으면 해당 PR 번호를 사용자에게 알린다
  - 없으면 (머지·닫힘·미생성) 즉시 새 PR을 열고 번호를 알린다
  - "PR에 반영되었습니다"는 확인 없이 절대 말하지 않는다

## PR 생성 후 테스트 실행 루틴

PR을 연 직후 Test Plan의 각 TC를 직접 실행하고 결과를 사용자에게 보고한다.

### 테스트 유형별 도구

| 테스트 유형 | 도구 | 실행 조건 |
| ----------- | ---- | --------- |
| API E2E | `curl` + `$BACKEND_HOST` (`.env` 로드) | 항상 실행 |
| 백엔드 로그 확인 | `GET $BACKEND_HOST/api/v1/logs` | API 테스트 후 |
| DB / 플러그인 단위 | `pytest` (`.venv`) | 관련 파일 수정 시 |
| 프론트엔드 UI | playwright MCP (`browser_navigate` → `browser_snapshot`) | UI 변경 시 |

### 실행 절차

1. `source integrated_PARK/.env` 로 환경변수 로드
2. TC 번호 순서대로 각 테스트 실행
3. 각 TC마다 `✅ PASS` / `❌ FAIL` 결과 출력
4. FAIL 발생 시 — 즉시 수정 후 동일 브랜치에 커밋 → 재테스트
5. 전체 PASS 확인 후 "테스트 완료 — PR #번호 머지 가능" 보고

### 실행 불가 예외

- 로컬 서버 미기동 상태의 localhost 테스트 → 사용자에게 기동 요청
- Azure Container Apps cold start → 30초 대기 후 1회 재시도

## 세션 인수인계

다음 중 하나라도 해당되면 즉시 인수인계 문서를 생성한다:

- 대화 턴이 20회를 초과한 경우
- 에러 해결 없이 동일 문제를 3회 이상 반복한 경우
- 작업 범위가 최초 요청에서 3개 이상의 파일로 확장된 경우

생성 절차:

1. 사용자에게 알린다: `"⚠️ 인수인계 트리거 발동 — 인수인계 문서를 생성합니다."`
2. `docs/session-reports/YYYY-MM-DD-handoff.md`를 생성한다 (브랜치명, 수정 파일 목록, 에러·미완료 작업, 다음 세션 인수 요약 3–5줄 포함)
3. 새 세션은 해당 파일을 읽어 맥락을 즉시 복원한다

## Memory 저장 기준

| 저장 위치 | 저장 대상 |
| --------- | -------- |
| `CLAUDE.md` | 팀 전체 영구 규칙, 빌드·실행 명령, 아키텍처 결정 |
| `~/.claude/.../memory/` | CLAUDE.md에 없는 개인 피드백, 프로젝트 일시 상태 |

- CLAUDE.md에 이미 있는 규칙은 Memory에 중복 저장하지 않는다
- 새 패턴을 Memory에 먼저 저장 → 세션 3회 이상 반복 시 CLAUDE.md로 이전

## 백엔드 로그

배포: Azure Container Apps. `integrated_PARK/.env`의 `BACKEND_HOST` 참조.

```bash
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -m json.tool
```

상세 명령 및 필터링: [`docs/guides/backend-logs.md`](docs/guides/backend-logs.md)

## 주의 사항

- `.env` 파일에는 Azure API 키가 있음 — 절대 커밋하지 말 것
- `integrated_PARK/.venv/`는 gitignore됨

## 반복 실수 패턴

<!-- Claude가 반복적으로 틀린 사항을 여기에 기록. 주기적으로 업데이트. -->
