# Azure 신규 테넌트 인프라 Foundation 구축 세션 인수인계

## 세션 요약

이전 세션 인수인계(`2026-04-27-azure-tenant-bootstrap-handoff.md`)의 [next] 항목 1~4번을 진행했다. PR #328 머지 후 detect한 회귀를 핫픽스로 복구하고, OIDC 자동 배포 파이프라인 + Container Apps + Cosmos까지 구축. 라이브 서비스(구 환경)는 무영향.

## 머지 PR 목록

| PR | 제목 | 비고 |
|----|------|------|
| [#329](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/329) | docs: Azure 이전 전략 기획안 + 세션 인수인계 | 로컬 산출물 위치 정리 (data/legal/raw, artifacts, backups gitignore) |
| [#331](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/331) | ci: Bicep what-if/deploy 워크플로 (신규 테넌트 OIDC) | App Reg + Federated Cred + AZURE_*_B secrets |
| [#332](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/332) | feat: Container Apps Environment + backend Container App | auto-deploy 후 회귀 발생 |
| [#333](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/333) | fix: Container App 첫 부트스트랩 — registries 분기 + AcrPull | #332 핫픽스 |
| [#334](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/334) | feat: Cosmos DB Serverless + 6 컨테이너 | Data Contributor 역할 자동 부여 |

## 현재 rg-sohobi-prod 자원 (6종)

| 자원 | 종류 | 상태 |
|------|------|------|
| `sohobi-logs` | Log Analytics | 30일 보존, 0.5GB cap |
| `sohobiprodlogs` | Storage Account + blob `sohobi-logs` | LRS, public access off |
| `sohobiprodacr` | ACR | Basic |
| `sohobi-prod-env` | Container Apps Environment | Consumption profile |
| `sohobi-backend` | Container App | minReplicas=0, FQDN HTTP 200 (quickstart placeholder) |
| `sohobi-prod-cosmos` | Cosmos DB | Serverless, AAD-only, 6 컨테이너 |

## 외부 인프라 변경

- 신규 테넌트(B) `sohobi-github-actions` App Registration + SP 생성
- SP 권한: `Contributor` + `Role Based Access Control Administrator` on `rg-sohobi-prod`
- Federated Credentials 2개: `github-main` (push deploy), `github-pr` (what-if)
- GitHub Repo Secrets 신규: `AZURE_CLIENT_ID_B`, `AZURE_TENANT_ID_B`, `AZURE_SUBSCRIPTION_ID_B`

## 핵심 학습 (회귀 방지)

1. **Bicep `registries` 설정과 ACR AcrPull 권한의 chicken-and-egg**: 같은 deploy에서 system identity 생성 + role 부여 + registries 검증이 동시에 일어나면 무한 대기 timeout. → `useAcrImage` param으로 분기. 첫 부트스트랩은 public image, 실제 backend 이미지 배포 시 `useAcrImage=true`로 전환.
2. **liveness probe placeholder 호환성**: `livenessProbePath` 빈 문자열 시 probe 미설정. 실제 backend 배포 시 `/api/v1/health` 등으로 override.
3. **로컬 사전 deploy = 회귀 비용 절감**: GitHub Actions auto-deploy timeout 22분 vs 로컬 즉시 검증. 이번 세션 #334 cosmos는 로컬 사전 검증 거쳐 한 번에 통과.

---

<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-27-azure-tenant-bootstrap-handoff.md

[unresolved]
- (carry from prev) MED gov-programs-index 원본 데이터 — 외부 블로커
- (carry) MED 신규 구독 budget 알람 미설정
- (carry) LOW DNS cutover 옵션 A vs B 미결정
- (carry) LOW usage_events Cosmos 컨테이너 backend reference 미확인
- LOW sohobi-backend는 quickstart placeholder 상태 — 실제 backend 이미지 배포(`useAcrImage=true`, livenessProbePath, targetPort=8000) 필요

[decisions]
- Container App 첫 부트스트랩은 public image로 통과시키고 ACR pull은 별도 단계로 분리 (Bicep useAcrImage 분기)
- Cosmos는 Serverless + disableLocalAuth=true + AAD 데이터 평면 인증으로 통일. backend Container App system identity에 built-in Data Contributor(00000000-0000-0000-0000-000000000002) 자동 부여
- Bicep deploy SP는 RBAC Admin 추가 (Bicep 내 roleAssignment write 권한)
- 로컬 사전 deploy를 PR push 전 의무 단계로 채택 — auto-deploy timeout 회귀 비용 회피

[next]
1. PR #5 PostgreSQL Flexible Server B1ms 모듈 (autostop=false, 야간 정지는 cron으로 별도)
2. PR #6 OpenAI(gpt-5.4-mini + text-embedding-3-small + text-embedding-3-large) + AI Search Basic
3. PR #7 Static Web App (sohobi.net custom domain)
4. PG 야간 정지 cron (.github/workflows/pg-nightly-stop.yml)
5. RG-scope budget 알람 (실패 시 태그 기반)
6. import 파이프라인: 02_cosmos_export.py 역방향 + azcopy + pg_dump→psql
7. legal-index v2 빌드 (data/legal/raw → 파이프라인 #325 트리거)
8. 실 backend 이미지 배포 (sohobi-backend useAcrImage=true 전환)
9. docs/runbooks/azure-cutover.md (D-day 분 단위)

[traps]
- (carry) 신규 구독 RBAC 조회 시 UPN 대신 object-id 사용
- (carry) Bicep CLI ~/.azure/bin 0바이트 파일 잔존 시 rm 후 재설치
- Container App `registries: [{...identity:'system'}]`은 AcrPull 부여 전엔 무한 대기 timeout (22분). useAcrImage=false로 첫 부트스트랩 통과시키는 것이 유일 해결
- Cosmos Bicep what-if는 sqlRoleAssignment에서 unsupported 1건 출력 — deploy-time principalId 의존이라 분석 불가, 무시 OK
- 로컬 az cli 컨텍스트는 신규 테넌트(B)로 고정. 구 환경 자원 조회 시 az account set 필요
CLAUDE_HANDOFF_END -->
