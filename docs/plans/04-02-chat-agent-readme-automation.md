# 플랜: 안내 에이전트 표시 · README 최신화 · 자동화 워크플로우

## Context
chat_agent.py가 오케스트레이터에서 '안내' 도메인으로 동작하지만, 프론트엔드 일부 컴포넌트에서 누락되어 있음. README도 Oracle DB 참조 등 구식 정보를 포함. chat_agent의 시스템 프롬프트도 GovSupportPlugin/AdminProcedurePlugin 추가 기능을 반영하지 않음.

---

## 작업 1: 프론트엔드 '안내' 레이블 추가

현재 상태 분석:
- `ResponseCard.jsx:4` — `chat: "안내"` **이미 존재** ✅
- `ProgressPanel.jsx:5-10` — `DOMAIN_LABEL`에 `chat` **누락** ❌
- `LogTable.jsx:5-11` — `DOMAIN_KR`, `DOMAIN_STYLE`에 `chat` **누락** ❌

### 수정 1-A: `frontend/src/components/ProgressPanel.jsx` (line 5-10)
```js
// Before
const DOMAIN_LABEL = {
  admin:    "행정·신고",
  finance:  "재무·시뮬레이션",
  legal:    "법률·세무",
  location: "상권 분석",
};

// After
const DOMAIN_LABEL = {
  admin:    "행정·신고",
  finance:  "재무·시뮬레이션",
  legal:    "법률·세무",
  location: "상권 분석",
  chat:     "안내",
};
```

### 수정 1-B: `frontend/src/components/LogTable.jsx` (line 5-11)
```js
// DOMAIN_KR — chat 추가
const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무", location: "상권분석", chat: "안내" };

// DOMAIN_STYLE — chat 스타일 추가 (purple, ResponseCard와 동일)
const DOMAIN_STYLE = {
  ...기존...,
  chat: { background: "rgba(139,92,246,0.12)", color: "#8b5cf6" },
};
```

---

## 작업 2: `integrated_PARK/README.md` 전반 수정

### 변경 항목
1. **아키텍처 다이어그램**
   - `chat` 도메인 분기 추가 (Sign-off 바이패스 명시)
   - `AdminProcedurePlugin` 추가 (admin 분기)
   - Oracle → PostgreSQL (Azure) 수정 (location 분기)
2. **필수 조건** — Oracle DB → PostgreSQL (Azure) 로 교체
3. **환경 변수 표** — `ORACLE_*` 5개 → `PG_*` 5개로 교체
4. **도메인 분류 기준 표** — `chat` 도메인 행 추가, admin 플러그인에 AdminProcedurePlugin 추가
5. **폴더 구조** — `agents/chat_agent.py`, `map_router.py` 추가, `plugins/admin_procedure_plugin.py` 추가

---

## 작업 3: `integrated_PARK/agents/chat_agent.py` SYSTEM_PROMPT 최신화

### 변경 항목
- **[1] 행정 에이전트**: 정부지원사업(보조금, 창업패키지, 대출/융자, 신용보증, 고용지원, 교육/컨설팅) 안내 추가, AdminProcedurePlugin 기반 5가지 절차(영업신고·위생교육·사업자등록·보건증·소방) 명시
- **[2] 재무 시뮬레이션 에이전트**: 히스토그램 차트 출력 가능 언급
- **[3] 법무 에이전트**: 내용 유지 (변경 없음)
- **[4] 상권 분석 에이전트**: "Oracle" 제거, "2024년 4분기 서울 PostgreSQL DB 기반" 명확화

---

## 작업 4: 자동화 워크플로우 제안

docs/plans/2026-04-02-agent-readme-sync-workflow.md 에 문서 저장.

### 제안 방식
`scripts/sync_readme_prompt.py` 스크립트 (또는 Claude Code Hook):

**수동 실행 방식 (권장, 즉시 구현 가능)**
```
python scripts/sync_readme_prompt.py
```
- agents/*.py 각 파일 상단 docstring + SYSTEM_PROMPT 읽기
- plugins/*.py kernel_function 목록 파싱
- README.md 특정 섹션(마커 주석 `<!-- AGENTS_START -->` ~ `<!-- AGENTS_END -->`) 덮어쓰기
- chat_agent.py의 SYSTEM_PROMPT 에이전트 설명 블록만 교체

**Claude Code Hook 방식 (향후)**
- PostToolUse hook: agents/*.py 편집 시 자동으로 sync 스크립트 실행
- settings.json에 등록

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/components/ProgressPanel.jsx` | `DOMAIN_LABEL`에 `chat: "안내"` 추가 |
| `frontend/src/components/LogTable.jsx` | `DOMAIN_KR`, `DOMAIN_STYLE`에 `chat` 추가 |
| `integrated_PARK/README.md` | 아키텍처·환경변수·폴더구조 전반 수정 |
| `integrated_PARK/agents/chat_agent.py` | `SYSTEM_PROMPT` 에이전트 설명 최신화 |
| `docs/plans/2026-04-02-agent-readme-sync-workflow.md` | 자동화 워크플로우 문서 |

---

## 검증

```bash
# 프론트엔드: chat 도메인 응답 후 ProgressPanel/LogTable에 '안내' 표시 확인
npm run dev  # frontend/

# 백엔드: chat 도메인 라우팅 확인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "상권 분석 에이전트 어떻게 사용해요?"}'
# → domain: "chat", draft에 안내 내용 확인
```
