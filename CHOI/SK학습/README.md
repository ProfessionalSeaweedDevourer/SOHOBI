# SK 학습 (Semantic Kernel F&B 창업 지원 시스템)

Azure OpenAI + Semantic Kernel을 활용한 F&B 창업 지원 멀티 에이전트 시스템 PoC입니다.

## 폴더 구성
```
SK학습/
├── fnb_sk_step01_kernel_plugin.ipynb   # Kernel & Plugin 기초
├── fnb_sk_step02_fixed.ipynb           # ChatCompletionAgent 단일 에이전트
├── fnb_sk_step03_fixed.ipynb           # AgentGroupChat 멀티 에이전트
├── fnb_sk_step04_fixed.ipynb           # MCP 연동 (서울시 상권분석 API)
├── fnb_sk_step05_fixed.ipynb           # Process Framework (HITL + Sign-off)
├── fnb_sk_step06_agent_pipeline.ipynb  # 에이전트 간 데이터 교류 파이프라인
├── fnb_sk_step07_orchestrator.ipynb    # 오케스트레이터 + 사용자 입력 테스트
├── seoul_commercial_mcp_server_sse.py  # 서울시 상권분석 MCP 서버 (SSE)
├── law_mcp_server.py                   # 국가법령정보 MCP 서버 (실존하지않는 가상의 임시서버로 학습용이었음)
├── .env                                # API 키 설정 (Azure OpenAI, 서울시 API)
└── test/                               # 실제 테스트 실행 폴더 (아래 참고)
```

> ⚠️ 실제 테스트는 `CHOI/SK학습/test` 폴더에서 이루어졌습니다.
> 노트북 실행 시 MCP 서버(`seoul_commercial_mcp_server_sse.py`)가 먼저 실행 중이어야 합니다.

## 학습 단계별 설명

| Step | 파일 | 핵심 개념 |
|------|------|-----------|
| 01 | `step01` | `@kernel_function` 으로 Python 함수를 LLM 툴로 등록 |
| 02 | `step02` | `ChatCompletionAgent` 단일 에이전트, Azure RAI 우회 |
| 03 | `step03` | `AgentGroupChat` 멀티 에이전트, LLM 기반 에이전트 선택/종료 전략 |
| 04 | `step04` | MCP SSE 서버 연동, 서울시 오픈API 페이지네이션 |
| 05 | `step05` | `ProcessBuilder` + `KernelProcessStep` 워크플로우 |
| 06 | `step06` | Step 간 데이터 전달, 조건부 분기 (상권→재무→리포트) |
| 07 | `step07` | 오케스트레이터 LLM 도메인 분류 + 자유 입력 테스트 |

## 시스템 아키텍처
```
사용자 자연어 입력
    ↓
[OrchestratorAgent]  LLM이 도메인 판단
    ├─ map      → LocationAgent (서울시 상권분석 MCP)
    ├─ finance  → FinanceAgent (BEP 계산)
    ├─ pipeline → 상권→재무→대안지역→리포트 파이프라인
    └─ unknown  → 안내 메시지
```

## MCP 서버 실행
```bash
# 서울시 상권분석 MCP 서버 (포트 8001)
python seoul_commercial_mcp_server_sse.py
```

## 환경 설정 (.env)
```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
SEOUL_API_KEY=...
```

## 주요 이슈 해결 이력

- Azure RAI 필터 우회: 한국어 입력 → 영어 변환 후 LLM 전달
- MCP Windows 호환: `MCPStdioPlugin` → `MCPSsePlugin` 전환
- 서울시 API: 쿼리스트링 미지원 → 1000건 페이지네이션 + Python 필터링
- 행정동 코드 검증: 홍대 = 서교동 `11440660`, 카페 = `CS100010`
