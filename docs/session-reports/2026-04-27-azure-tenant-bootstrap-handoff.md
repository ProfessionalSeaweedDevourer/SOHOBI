# 2026-04-27 — Azure 신규 테넌트 진입 + Bicep IaC foundation

## 한 줄 요약

별도 테넌트·구독 이전 기획 작성부터 시작해서, AI Search legal-index 재구축 파이프라인 구현 + Cosmos·Blob 백업 자동화 + 신규 구독 진입 + Bicep foundation 모듈 deploy 직전까지 도달. 누적 PR 3건(#325 #326 #328) open 상태.

## 브랜치

현재: **`feat/park-azure-bicep-foundation`** (HEAD `edeb7f2`)

이전 세션 이후 main 진척:
- `599652d` docs: Azure 별도 테넌트·구독 이전 1차 기획안 (본 세션 시작에 main 직접 push)

## 본 세션 누적 PR

| PR | 브랜치 | 내용 | 상태 |
|----|--------|------|------|
| #325 | `feat/park-legal-index-rebuild` | legal AI Search 인덱스 재구축 6단계 파이프라인 + 평가 + RAG 기획 | OPEN |
| #326 | `feat/park-azure-migration-prep` | Azure 이전 사전준비 6단계 스크립트 + 런북 + 1차 백업 실행 결과 | OPEN |
| #328 | `feat/park-azure-bicep-foundation` | Bicep IaC foundation (Log Analytics + Storage + ACR) | OPEN, deploy 미수행 |

## 수정·추가 파일 (커밋 분포)

### 본 세션에서 main 직접 push (이미 머지됨)
- `docs/plans/2026-04-26-azure-tenant-migration.md` — Azure 별도 테넌트 이전 1차 기획안

### PR #325 (legal index)
- `docs/plans/2026-04-26-legal-index-rebuild.md`
- `scripts/legal_index/01_clean.py` ~ `06_verify.py` + `eval.py` + `README.md`
- `data/legal_eval_set.template.jsonl`
- `.gitignore` (artifacts·data·원본 JSON 제외)

### PR #326 (migration prep)
- `scripts/migrate/00_preflight.sh` ~ `05_search_schema_export.py`
- `docs/runbooks/azure-migration-prep.md`
- `.gitignore` (`backups/` 제외)

### PR #328 (Bicep foundation)
- `infra/bicep/main.bicep` + `parameters/prod.bicepparam`
- `infra/bicep/modules/log-analytics.bicep` / `storage.bicep` / `acr.bicep`
- `.gitignore` (`infra/bicep/main.json` 제외)

### Uncommitted (현재 워킹 트리)
- `docs/plans/strategic/azure-cost-and-tenant-strategy.md` — 본 세션 합의 통합 전략 문서 (다음 세션에서 main 직접 push 또는 별도 PR로 정리 필요)
- `backups/` — 외부 보관 (Cosmos·Blob·Azure snapshot, gitignored)
- `artifacts/` — legal index dry-run 산출물 (gitignored)
- `law_data_for_embedding*.json`, `refined_law_data*.json` — 원본 (gitignored)

## 신규 Azure 환경 (실제 생성됨)

| 항목 | 값 |
|------|-----|
| Tenant ID | `5555704e-be9c-41ff-852f-2ed5c68989b2` |
| Tenant Domain | `erikjparkgmail.onmicrosoft.com` |
| Subscription ID | `eba83124-c3b9-4a07-be43-e0c9acdc3425` |
| Subscription Name | `Azure subscription 1` |
| User UPN (RBAC) | `erik.j.park_gmail.com#EXT#@erikjparkgmail.onmicrosoft.com` |
| User Object ID | `0fe41299-7e94-43d0-baf2-d29aaa7ba339` |
| Role | Owner (구독 scope) |
| Resource Group | `rg-sohobi-prod` (koreacentral) |
| 등록된 RP | App, DocumentDB, DBforPostgreSQL, Search, CognitiveServices, Storage, Network, ContainerRegistry, Web, OperationalInsights, Insights, ManagedIdentity (12 + Authorization 자동) |

## 본 세션 진행 단계

### Phase 1 — 기획 & 전략 수립
1. **Azure 별도 테넌트 이전 기획안** 작성 (Phase 0~3 cutover 절차, 데이터 export/import vs 재배포 분류표, 옵션 A/B DNS 전환)
2. **Legal AI Search 인덱스 재구축 RAG 기획** — 입력 4개 JSON 분석 (배치 1+2 = 31개 법령 3,996 chunks), 전처리 품질 평가 (HIGH issue 3건: title-only 청크, articleTitle 누락, 표 노이즈), 신규 인덱스 v2 schema 설계, 평가셋 100문항 + Recall@5/MRR/nDCG@10
3. **Strategic Plan 통합 작성** — 서비스 정체성 재정의(portfolio·개발용), 3축 전략(테넌트 분리 / right-sizing / 인덱스 재구축), 시퀀싱, 비용 시뮬($97 → $40~50 목표)

### Phase 2 — 구현
4. **Legal index 파이프라인 6단계 + 평가 스크립트** 구현. 1·2단계 dry-run 검증: 3996→3904 (title-only 92개 제거, hasTable 107개 플래그)
5. **Azure 이전 사전 백업 6단계 스크립트** 구현 + 1차 실측 실행:
   - Cosmos 6 컨테이너 3,559 docs (실제 컨테이너: `sessions`, `roadmap_votes`, `checklist`(단수), `feedback`, `users`, `usage_events`)
   - Blob 3 blobs 2.9MB
   - Azure 리소스 인벤토리 + RBAC + Container App env vars
   - AI Search schema: legal **ERR** (`choiasearchhh` 외부 계정 접근 차단 — 의존 제거 결정 정당화), gov 정상 (7,019 docs, 22 fields)

### Phase 3 — 비용·SKU 분석
6. **Cosmos over-provisioning 가설 검증** → ❌ 사실 아님. 이미 Serverless ($0.07/30일). cost-architecture.md와 reconcile하여 **PG B2s 24/7 ($49/월) + Defender ($20/월)** 가 진짜 right-sizing 대상임을 확인
7. **portfolio 정체성 명시** — 채용담당자 산발 접속 + 본인 개발. SLA 무필요. 야간 정지 + minReplicas 0 + Defender Free 모두 합리적

### Phase 4 — 신규 구독 진입 + Bicep foundation
8. 신규 테넌트 device-code 로그인 (사용자 별도 터미널) → `~/.azure/` 캐시 공유로 본 세션이 활용
9. RP 12개 등록 + RG `rg-sohobi-prod` 생성
10. OpenAI 모델 가용성 확인: gpt-5.4 시리즈 + text-embedding-3-small/large 모두 koreacentral 가용 → 리전 통합 가능
11. Bicep CLI 설치 (권한 에러 → `~/.azure/bin` 정리 후 재설치)
12. Bicep main + 3 모듈 작성 → `az bicep build` 통과 → what-if 5 자원 생성 미리보기 OK → PR #328

## 미완료·다음 세션 인수 (3-5줄)

1. **PR #325/#326/#328 admin merge 결정** — 코드 검토 후 머지. 본 세션 모든 작업이 미머지 상태
2. **PR #328 실제 deploy 실행** — what-if 통과한 5 자원(Log Analytics·Storage·ACR) 신규 구독에 생성
3. **Bicep 후속 모듈 작성**: Container App + env / Cosmos (Serverless) / PostgreSQL (B1ms) / Azure OpenAI + 모델 deployments / AI Search (Basic) / Static Web App
4. **GitHub Actions OIDC federated credential** 신규 테넌트에 등록 → `.github/workflows/deploy-backend.yml`이 신구독에서 작동하도록 `_B` suffix secrets 추가
5. **PG 야간 정지 cron** + **데이터 import 파이프라인**(PR #326 export → 신규 구독 자원으로 push) + **cutover 런북** 작성

## 결정 판정 — 이전 세션 unresolved 재평가

**이전 handoff** (`2026-04-21-career-kr-build-handoff.md`)의 `[unresolved]`:

1. **MED (carry:4) legal-index + gov-programs-index 원본 데이터 확보**
   - **legal 부분 → CLOSED**: 사용자가 본 세션에 4개 JSON(배치 1+2, 31개 법령 3,996 chunks) 직접 제공. PR #325의 dry-run으로 동작 확인. 외부 블로커 우회 성공
   - **gov 부분 → carry:5**: 정부지원사업 원본은 여전히 미확보. carry 5에 도달했으나 (a) 외부 블로커가 여전히 active이고 (b) 본 세션에서 명시적 워크스트림으로 분리 추적 결정 (전략 §3-C, runbook §7)이라 closure 부적절. 지속 추적

2. **MED (carry:2) Phase 2 sohobi-search-kr 실행 go/no-go**
   - **INVALIDATED**: 전제(구 구독 `rg-ejp-9638` 내에 sohobi-search-kr 추가)가 무너짐. 본 세션에서 신규 테넌트·구독으로 전체 통합 이전 결정 → 신규 환경에서 `sohobi-search` 신규 자원으로 빌드. 구 구독 내 추가 불필요

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-azure-bicep-foundation
pr: 328
prev: 2026-04-21-career-kr-build-handoff.md

[unresolved]
- MED (carry:5) gov-programs-index 원본 데이터 확보 — 외부 블로커(이관 팀원). closure 불가, 신규 환경에서도 동일 이슈. legal 부분만 separately CLOSED
- MED 신규 구독 budget 알람 미설정 — Cost Management API는 접근 OK. RG-scope budget 시도 또는 태그 기반 우회 필요
- LOW DNS cutover 옵션 A(완전 이전) vs B(A record만 변경) 미결정 — cutover 직전 트래픽 패턴 보고 결정. 기획안 §Phase 2는 B 권장 후 안정화 시 A
- LOW usage_events Cosmos 컨테이너(3,256 docs)가 backend code에 어떻게 reference되는지 미확인 — 단순 telemetry라면 import 우선순위 낮춤 가능

[decisions]
- CLOSED: legal 원본 데이터 확보 — 사용자 직접 4개 JSON 제공 (refined_law_data{,_1}.json + law_data_for_embedding{,_1}.json), 31개 법령 3,996 chunks
- INVALIDATED: Phase 2 sohobi-search-kr (구 구독 내 추가) — 신규 테넌트 통합 이전으로 superseded. 신규 환경 sohobi-search Basic으로 대체
- 신규 환경: tenant=5555704e-...erikjparkgmail.onmicrosoft.com, sub=eba83124-..., RG=rg-sohobi-prod, region=koreacentral 통합
- Right-sizing 채택: PG B1ms / Container App minReplicas 0 / Defender Free / OpenAI 핵심 모델만 / Log Analytics 30일+0.5GB cap
- AI Search 2단계: Phase 1 Basic($75/월) → 평가셋(eval.py) 안정 후 Phase 2 Option 3 (rank_bm25 + numpy + Blob 인덱스) 전환. eval.py가 회귀 검증 게이트
- legal-index 외부 계정 의존(`choiasearchhh`) 끊기로 확정 — 본 세션 schema export ERR로 접근 차단 직접 확인. 신규 환경에서 빈 인덱스 생성 후 PR #325 파이프라인으로 빌드
- Cosmos는 Serverless라 over-provisioning 자체가 불가. 빌링 절감 여지는 PG·Defender 쪽

[next]
1. PR #325/#326/#328 코드 검토 후 admin merge
2. PR #328 deploy: az deployment group create -g rg-sohobi-prod --template-file infra/bicep/main.bicep --parameters @prod.bicepparam → 5 자원 생성
3. uncommitted strategic plan(docs/plans/strategic/azure-cost-and-tenant-strategy.md) main에 별도 push 또는 후속 PR에 포함
4. Bicep 후속 모듈: container-apps-env + container-app(minReplicas=0) → cosmos(Serverless) → postgres(B1ms) → openai(gpt-5.4-mini + embeddings) → ai-search(Basic) → static-web-app
5. GitHub Actions OIDC federated credential 등록 (신규 테넌트 App Registration + repo secrets _B suffix)
6. 데이터 import 파이프라인 작성: 02_cosmos_export.py 역방향 + azcopy blob → 신규 자원
7. PG 야간 정지 cron (GitHub Actions schedule, az postgres flexible-server start/stop)
8. docs/runbooks/azure-cutover.md 작성 (D-day 분 단위 절차)

[traps]
- 신규 구독 RBAC 조회 시 UPN(erik.j.park@gmail.com)으로 실패. external guest는 `erik.j.park_gmail.com#EXT#@erikjparkgmail.onmicrosoft.com` 형태로 저장됨. object-id(`az ad signed-in-user show --query id`) 사용
- Cosmos 신규 자원도 default로 Local Auth 비활성될 가능성. 02_cosmos_export.py에 이미 AAD 폴백 구현되어 있어 import 스크립트도 동일 패턴 적용
- Bicep CLI 첫 설치 시 ~/.azure/bin/bicep 0바이트 파일 잔존하면 권한 에러. rm -rf ~/.azure/bin 후 az bicep install 재실행
- az login 백그라운드 실행 시 stdout 버퍼링으로 device code 미표시 — 사용자에게 별도 터미널 인증 권장 (~/.azure/ 캐시 공유)
- legal-index v2 빌드 시 azure-search-documents SDK Field 정의에서 ko.lucene analyzer는 LexicalAnalyzerName.KO_LUCENE 상수로 직접 참조 (PR #325 05_upload.py 참조)
CLAUDE_HANDOFF_END -->
