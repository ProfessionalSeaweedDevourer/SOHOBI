# docs/architecture

SOHOBI 시스템 아키텍처를 시각화한 Mermaid 다이어그램 모음. 각 파일은 브라우저에서 직접 열 수 있는 HTML 형식.

---

## 다이어그램 목록

| 파일 | 설명 |
|------|------|
| [P1_sohobi_mermaid_architecture.html](P1_sohobi_mermaid_architecture.html) | 전체 시스템 아키텍처 — API Server → DomainRouter → 5개 에이전트 흐름 |
| [P2_sohobi_admin_agent_azure.html](P2_sohobi_admin_agent_azure.html) | 행정 에이전트 상세 — AdminProcedurePlugin + GovSupportPlugin 구조 |
| [P3_sohobi_finance_agent_azure.html](P3_sohobi_finance_agent_azure.html) | 재무 에이전트 상세 — 4단계 파이프라인 + 몬테카를로 시뮬레이션 |
| [P4_sohobi_legal_agent_azure.html](P4_sohobi_legal_agent_azure.html) | 법률 에이전트 상세 — Azure AI Search 기반 법령 RAG |
| [sohobi_location_agent_azure.html](sohobi_location_agent_azure.html) | 상권분석 에이전트 상세 — PostgreSQL DB 조회 + LLM 분석 파이프라인 |
| [sohobi_terry_architecture.html](sohobi_terry_architecture.html) | 프론트엔드 + 지도 모드 아키텍처 (OpenLayers 기반) |
| [architecture-diagram-v2.html](architecture-diagram-v2.html) | 통합 아키텍처 v2 — 세션 관리, Sign-off, SSE 스트리밍 포함 |
| [cost-architecture.md](cost-architecture.md) | Azure 비용 아키텍처 — 리소스 인벤토리, 30일 실측 비용, 예산 가이드, 절감 액션 |
