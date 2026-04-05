# 에이전트·README 동기화 자동화 워크플로우

**작성일:** 2026-04-02

---

## 배경 및 문제

에이전트(`agents/*.py`)나 플러그인(`plugins/*.py`)이 변경될 때, 두 곳을 수동으로 함께 업데이트해야 합니다:

1. `integrated_PARK/README.md` — 아키텍처·도메인 분류 표·폴더 구조
2. `agents/chat_agent.py`의 `SYSTEM_PROMPT` — 사용자에게 보이는 에이전트 설명

수동 관리 시 README와 실제 코드가 어긋나는 drift가 발생하기 쉽습니다.

---

## 제안 방식

### 방식 A: `scripts/sync_readme_prompt.py` 수동 실행 스크립트 (권장)

에이전트·플러그인 변경 후 한 번 실행하면 README의 마킹된 구간과 chat_agent의 에이전트 설명 블록을 자동으로 갱신합니다.

#### 사용법

```bash
cd integrated_PARK
.venv/bin/python scripts/sync_readme_prompt.py
```

#### 동작 원리

1. **에이전트 메타 수집** — `agents/*.py` 파일 상단 docstring과 `SYSTEM_PROMPT` 내 `[N]` 섹션 파싱
2. **플러그인 메타 수집** — `plugins/*.py`에서 `@kernel_function` 데코레이터가 붙은 함수 목록 추출
3. **README 구간 교체** — `<!-- AGENTS_START -->` ~ `<!-- AGENTS_END -->` 마커 사이의 도메인 분류 표·아키텍처 블록 덮어쓰기
4. **chat_agent SYSTEM_PROMPT 갱신** — `[1] 행정 에이전트` ~ `[4] 상권 분석 에이전트` 블록만 교체 (응답 원칙은 수동 관리)

#### README 마커 규칙

```markdown
<!-- AGENTS_START -->
| 도메인 | 해당 질문 유형 | 활성화되는 데이터 소스 |
...
<!-- AGENTS_END -->
```

스크립트는 이 두 마커 사이의 내용만 덮어씁니다.

---

### 방식 B: Claude Code PostToolUse Hook (향후 선택)

에이전트 파일 편집 시 자동으로 sync 스크립트를 실행하도록 Claude Code 훅을 등록합니다.

#### `.claude/settings.json` 설정 예시

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'integrated_PARK/agents/'; then cd integrated_PARK && .venv/bin/python scripts/sync_readme_prompt.py; fi"
          }
        ]
      }
    ]
  }
}
```

- `agents/` 디렉토리 파일 편집 시에만 실행 (다른 파일 편집 시 무시)
- 스크립트 실패 시 훅 출력에 경고 표시

---

## 수동 관리 체크리스트 (스크립트 구현 전)

에이전트·플러그인을 변경할 때 아래 항목을 함께 확인하세요.

### 에이전트 추가·수정 시

- [ ] `integrated_PARK/README.md` — 아키텍처 다이어그램의 해당 분기 업데이트
- [ ] `integrated_PARK/README.md` — 도메인 분류 기준 표 업데이트
- [ ] `integrated_PARK/README.md` — 폴더 구조에 파일 추가
- [ ] `agents/chat_agent.py` — `SYSTEM_PROMPT` 해당 에이전트 설명 블록 수정
- [ ] 프론트엔드 — `DOMAIN_KR`, `DOMAIN_LABEL`, `DOMAIN_COLOR` 등 도메인 맵 업데이트

### 플러그인 추가·수정 시

- [ ] `integrated_PARK/README.md` — 아키텍처 다이어그램의 플러그인 목록 업데이트
- [ ] `integrated_PARK/README.md` — 도메인 분류 기준 표의 데이터 소스 컬럼 업데이트
- [ ] `integrated_PARK/README.md` — 폴더 구조에 파일 추가
- [ ] `agents/chat_agent.py` — 해당 에이전트 설명에 플러그인 기능 반영

### 환경 변수 추가 시

- [ ] `integrated_PARK/README.md` — 환경 변수 표 업데이트
- [ ] `integrated_PARK/.env` (예시 값으로)

---

## 현재 구현 상태 (2026-04-02 기준)

스크립트(`sync_readme_prompt.py`)는 아직 구현되지 않았습니다.
방식 A 스크립트 구현이 결정되면 이 문서를 업데이트하세요.

현재는 **수동 관리 체크리스트** 방식을 사용합니다.
