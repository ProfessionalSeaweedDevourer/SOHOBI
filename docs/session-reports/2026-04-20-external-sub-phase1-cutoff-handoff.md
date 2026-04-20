# 2026-04-20 외부 Azure 구독 Phase 1 절단 완료 handoff

외부 Azure 구독 (교육기관 관할 `sohobi-search` centralus + `sohobi-openai` eastus) 과 SOHOBI 백엔드의 **호출 경로를 완전 절단**. 1주 deadline 의 우리 측 책임 종결 지점까지 도달.

## 브랜치·커밋

- 브랜치: `main` (작업 브랜치 없이 직접 Azure 인프라만 변경)
- 커밋 없음. 코드·문서 수정 0건. 순수 Container App 런타임 설정 변경.

## 인프라 변경 요약

| 대상 | 변경 | 이유 |
| --- | --- | --- |
| Container App secret `gov-search-api-key` | → `"disabled"` | gov_support 외부 AI Search API key 비활성 |
| Container App secret `gov-openai-api-key` | → `"disabled"` | gov_support 외부 Azure OpenAI API key 비활성 |
| Container App secret `azure-search-endpoint` | → `"disabled"` | fallback placeholder 공백화 시도. Azure 가 `""` 비허용해 sentinel 주입 |
| Container App secret `azure-search-key` | → `"disabled"` | 동상 |
| Container App env `GOV_SEARCH_ENDPOINT` | **제거** | 외부 centralus AI Search 참조 제거 |
| Container App env `GOV_OPENAI_ENDPOINT` | **제거** | 외부 eastus Azure OpenAI 참조 제거 |
| Container App env `AZURE_SEARCH_ENDPOINT` | **제거** | gov 플러그인 fallback 차단 |
| Container App env `AZURE_SEARCH_KEY` | **제거** | 동상 |
| 신규 리비전 | `sohobi-backend--ext-cutoff-20260420` 트래픽 100% | 위 변경 반영 |
| 이전 리비전 | `sohobi-backend--0000183` 트래픽 0% (active 유지) | 롤백 대비 보존 |

**백업 파일** (우리 내부 파일시스템에만, gitignore 밖):

- `~/Documents/SOHOBI-backup/20260420/env-pre-cutoff.json`
- `~/Documents/SOHOBI-backup/20260420/secrets-pre-cutoff.json`

## 검증 결과 (2026-04-20 Phase 1 완료 게이트)

1. ✅ **gov_support 차단**: `/api/v1/query` 응답 draft 에 "지원 검색 서비스가 연결되지 않아" 명시 + 구체 사업명 부재. 플러그인 원본 가드 문자열(`추천 서비스가 설정되지 않았습니다`) 은 LLM paraphrase 로 변형됨 — 기능적 PASS
2. ✅ **외부 endpoint 호출 0**: `az containerapp logs show --tail 1000` 에서 `sohobi-search` / `sohobi-openai` 문자열 hit = 0
3. ✅ **회귀 없음**: finance(카페 시뮬레이션) / location(강남역 상권) / admin(세무) 전부 `status=approved`

## 미완료·후속

- Phase 2~6 은 deadline 밖. 사용자 go-ahead 필요:
  - Phase 2: `sohobi-search-kr` koreacentral Basic 프로비저닝 (~$75/월 신규 비용)
  - Phase 3: 원본 데이터 재확보 (교육기관 인계 / 내부 백업 / 공공 API 재크롤 / 영구 비활성)
  - Phase 4~6: 인덱스 재구축 → 재연결 → 문서·코드 정리
- 법무 에이전트 사용자 노출 대응 판단은 이전 handoff 부터 carry — 이제 gov_support 까지 무기능이므로 배너·비활성화 결정 체감 우선순위 상승
- 승인된 플랜 원문: `/Users/eric.j.park/.claude/plans/rg-ejp-imperative-newell.md`

## 이전 handoff unresolved 재판정

| 이전 항목 | 판정 | 근거 |
| --- | --- | --- |
| HIGH legal_search_plugin 무기능 (사용자 노출) | carried (carry:2) | 판정 미해결. gov_support 도 함께 무기능이 되어 대응 우선순위는 상승 |
| HIGH choiasearchhh 삭제 시점 추적 | **INVALIDATED** | 외부 구독 리소스 접근·추적 자체가 1주 deadline 원칙 위반. 교육기관 관할이라 추적 의미 소실 |
| MED legal-index 원본 데이터 확보 | carried (carry:2) | Phase 3 와 동일 이슈로 통합 |
| MED sohobi9638logs Blob 아카이브 탐색 | carried (carry:2) | 외부 RAG 시점 특정은 deadline 후 작업에서 불필요해짐. 다만 원본 데이터 단서 가능성 남아 유지 |
| MED Korea Central 통합 이관 계획 | **CLOSED (planning)** / carried (execution) | 플랜 문서 작성 완료(`~/.claude/plans/rg-ejp-imperative-newell.md`). 실행 Phase 2~5 는 carried |
| LOW `_available` placeholder 가드 강화 | carried (carry:2) | env 제거로 현 시점 공격 표면 0이나 재주입 회귀 방지 위해 guard 코드 추가 가치 여전 |

---

<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-20-legal-rag-dead-and-gov-env-sync-handoff.md

[unresolved]
- HIGH (carry:2) 법무+gov 에이전트 사용자 노출 대응 판단 보류. 둘 다 무기능 — 배너 / 비활성화 / 조용히 수리 결정 필요
- MED (carry:2) legal-index + gov-programs-index 원본 데이터 확보 경로 미확정. 교육기관 인계 / 내부 백업 / 공공 API 재크롤 / 영구 비활성 중 택일
- MED (carry:2) sohobi9638logs Blob 아카이브에서 구 RAG 원본 데이터 단서 탐색 여부 미결정 (시점 특정 목적은 소실됨)
- MED Phase 2 sohobi-search-kr koreacentral Basic 프로비저닝 go/no-go — ~$75/월 신규 비용 승인 필요
- LOW (carry:2) gov_support_plugin + legal_search_plugin `_available` placeholder 감지 가드 추가. env 재주입 회귀 방지

[decisions]
- 외부 구독 리소스 무접근 원칙: query·backup 목적이라도 billing(outbound bandwidth ~$0.05-0.09/GB) 및 권한 소멸 이슈로 금지. 원본 데이터는 정당한 경로로만 확보
- Azure Container App secret 은 `""` 비허용 — sentinel `"disabled"` 주입 + 연관 env var 자체 제거 조합으로 fallback 무력화
- Phase 1 완료 = 1주 deadline 의 우리 측 책임 종결. Phase 2~6 은 내부 기능 복구이며 deadline 과 분리
- 이전 리비전 `sohobi-backend--0000183` 은 Deactivate 하지 않고 트래픽 0% 로 보존 — 롤백 대비
- CLOSED: Korea Central 통합 이관 계획(planning portion). 플랜 문서 완성됨(~/.claude/plans/rg-ejp-imperative-newell.md)
- INVALIDATED: choiasearchhh 삭제 시점 추적. 외부 리소스 접근 금지 원칙 하에서 추적 자체가 목적 없음

[next]
1. 사용자 결정: 법무+gov 에이전트 사용자 노출 대응 (공통 배너 또는 개별 라우팅 분기)
2. Phase 2 승인 시 sohobi-search-kr 프로비저닝
3. Phase 3 원본 데이터 경로 확정 — 교육기관 인계 요청이 가장 정당한 경로
4. (승인 후) Phase 4 인덱스 스키마 + ingest 스크립트 작성
5. (Phase 5) gov_support 재연결 → secret/env 복원
6. (Phase 6) backend/.env.example 갱신 (placeholder 아닌 실제 내부 endpoint 값) + handoff 작성
7. (옵션) `_is_placeholder` 가드 PR — 재주입 회귀 방지

[traps]
- Azure Container App secret `""` 불허 — 빈 secret 시도 시 `ContainerAppSecretInvalid` 에러. sentinel 문자열 + env 제거 조합 필수
- gov secret `"disabled"` 는 truthy 값 — 연관 env var (`GOV_SEARCH_API_KEY` 등) 이 아직 secretRef 로 남아있음. 누군가 제거된 env(`GOV_SEARCH_ENDPOINT` 등)를 다시 추가하면 truthy 값이 주입되어 `_available=True` 복구됨 → 외부 호출 재개 위험
- `.env.example` placeholder 가 배포 파이프라인에서 Container App secret 으로 다시 주입된 사고 이력 (2026-04-03 `f2a620b` 이후 추정). Phase 6 갱신 시 실제 값 기재 또는 주입 스크립트 점검 필수
- text-embedding-3-large v1 (3072d) 전용 — gov index 재구축 시 동일 모델 버전 사용해야 벡터 호환. koreacentral 의 `text-embedding-3-large` 쿼터 사전 확인 필요
- TC1 검증: LLM 이 플러그인 guard 문자열을 paraphrase 하므로 literal grep 실패. 검증 기준은 "구체 사업명 부재 + 서비스 미연결 언급" + "로그에 외부 endpoint hit 0" 조합
CLAUDE_HANDOFF_END -->
