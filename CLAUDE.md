# SOHOBI 프로젝트 — Claude 영구 지시

## 빌드 & 실행 명령

```bash
# 백엔드 (integrated_PARK/)
cd integrated_PARK
.venv/bin/python3 api_server.py

# 프론트엔드 (frontend/)
cd frontend
npm run dev

# 의존성 설치
cd integrated_PARK && .venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

## 테스트

현재 공식 테스트 스위트 없음. API 동작 확인은 curl로:

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트 질문"}'
```

## 디렉토리 구조

| 경로 | 설명 |
|------|------|
| `integrated_PARK/` | **메인 통합 버전** — 실제 작동 코드 |
| `integrated_PARK/agents/` | 하위 에이전트 (법률·세무, 상권, 재무 등) |
| `integrated_PARK/api_server.py` | FastAPI 진입점 |
| `integrated_PARK/orchestrator.py` | Semantic Kernel 오케스트레이션 |
| `integrated_PARK/signoff/` | 최종 검증 에이전트 |
| `integrated_PARK/db/commercial.db` | 상권 SQLite DB (2024 Q4, 서울) |
| `frontend/` | React + Vite + Tailwind 프론트엔드 |
| `docs/session-reports/` | 세션 리포트 (날짜별) |
| `docs/architecture/` | 아키텍처 다이어그램 (HTML) |
| `docs/plans/` | 개선·테스트 플랜 문서 |
| `CHANG/`, `CHOI/`, `NAM/`, `PARK/`, `TERRY/` | 팀원별 개발 폴더 |

## 코드 규칙

- **Python**: 3.12 기준, `.venv/` 가상환경 사용
- **의존성**: `requirements.txt`에 `==` 버전 고정
- **백엔드**: FastAPI + Semantic Kernel + Azure AI Foundry (GPT-4o)
- **프론트엔드**: React + Vite + Tailwind CSS
- 에이전트 코드는 `integrated_PARK/agents/`에서만 수정

## PR / 커밋 규칙

- PR 본문에 "Generated with Claude Code" attribution 포함 금지
- 커밋 메시지: `type: 한국어 설명` (예: `fix: location 에이전트 버그 수정`)
- **PR 머지는 검증 완료 후에만 지시한다**: 코드 변경 후 curl 테스트 등으로 실제 동작을 확인하기 전까지 "PR을 머지하십시오"라고 지시하지 않는다. 검증 전 추가 수정이 필요하면 같은 브랜치에 커밋을 추가하고 열린 PR을 유지한다.

## 컴팩션 시 보존할 것

- 수정된 파일 목록
- 현재 발생 중인 에러 메시지
- 현재 브랜치명

## 백엔드 로그 가져오기

현재 배포 백엔드: **Azure Container Apps**
URL 및 시크릿은 `integrated_PARK/.env`의 `BACKEND_HOST`, `EXPORT_SECRET` 참조.

### 로그 조회 (curl — 권장)

현재 Azure Container Apps 백엔드는 로그를 Blob Storage에 기록하므로 `/api/v1/logs/export`(파일 다운로드)는 사용 불가. `/api/v1/logs` 읽기 API를 사용한다.

```bash
# .env에서 BACKEND_HOST, EXPORT_SECRET 로드 후 실행
source integrated_PARK/.env   # 또는 직접 값 입력

# 최근 N개 쿼리 조회 (type: queries | rejections | errors)
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -m json.tool

# 특정 시간대 필터링 (Python으로 파싱)
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=200" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data['entries']:
    if '2026-03-26T07:' <= e['ts'] <= '2026-03-26T09:':
        print(e['ts'], e.get('grade'), e.get('retry_count'), e.get('question','')[:60])
"
```

### 참고

- `scripts/pull_logs.py` — `BACKEND_HOST` 환경변수 기반 다운로드 스크립트 (Blob Storage 구성에서는 export 엔드포인트가 404 반환됨)
- `scripts/outdated/pull_logs_railway.py` — 구 Railway 백엔드용 스크립트 (사용 안 함)

## 주의 사항

- `integrated_PARK/db/commercial.db`는 대용량(13MB) — git에 이미 포함됨, 추가 업로드 불필요
- `.env` 파일에는 Azure API 키가 있음 — 절대 커밋하지 말 것
- `integrated_PARK/.venv/`는 gitignore됨
