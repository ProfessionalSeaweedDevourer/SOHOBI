# integrated_PARK/agents

SOHOBI 다중 에이전트 시스템의 5개 도메인 전문 에이전트.

`orchestrator.py`가 `domain_router.py`의 분류 결과에 따라 해당 에이전트를 호출한다.

---

## 에이전트 목록

| 파일 | 도메인 | 역할 | 플러그인 | 담당 |
|------|--------|------|----------|------|
| `admin_agent.py` | `admin` | 행정 절차 안내 + 정부지원사업 추천 | AdminProcedurePlugin, GovSupportPlugin, SeoulCommercialPlugin | NAM |
| `finance_agent.py` | `finance` | 재무 시뮬레이션 (4단계 파이프라인) | FinanceSimulationPlugin | CHANG |
| `legal_agent.py` | `legal` | 법률·세무 상담 (법령 RAG) | LegalSearchPlugin | CHOI |
| `location_agent.py` | `location` | 상권 분석 (DB 조회 + LLM 리포트) | CommercialRepository (직접 DB) | WOO |
| `chat_agent.py` | `chat` | 서비스 안내·일상 대화 | 없음 (Sign-off 바이패스) | PARK |

## 공통 동작

1. **창업자 프로필 주입** — 세션에 저장된 `founder_context`(업종, 지역, 예산 등)를 시스템 프롬프트에 삽입
2. **SSE 스트리밍** — `orchestrator.run_stream()`을 통해 토큰 단위 스트리밍 응답 지원
3. **Sign-off 검증** — `chat` 도메인을 제외한 4개 에이전트의 응답은 [`signoff/`](../signoff/)에서 품질 판정

## 도메인 라우팅

`domain_router.py`가 2단계로 질문을 분류:

1. **키워드 매칭** — 2개 이상 일치 시 즉시 반환 (confidence 0.85)
2. **LLM 분류** — 키워드 매칭 실패 시 GPT-4o JSON 분류 (fallback: `admin`)

## 관련 문서

- 플러그인 상세: [`../plugins/README.md`](../plugins/README.md)
- Sign-off 루브릭: [`../prompts/README.md`](../prompts/README.md)
- Sign-off 에이전트: [`../signoff/README.md`](../signoff/README.md)
