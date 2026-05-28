# 신규 테넌트(B) cutover 세부 기획

> 본 문서는 구 환경(`rg-ejp-9638`, 별도 테넌트)에서 신규 환경(`rg-sohobi-prod`, sub `eba83124-...`, 테넌트 `5555704e-...`)으로 라이브 서비스 이전을 위한 세부 실행 계획이다. 단일 점검 윈도우 1-2h 내 완료를 목표로 한다.

## 0. 현 상태 (고정 사실)

| 영역 | 상태 |
|------|------|
| 구 환경 (`rg-ejp-9638`) | 라이브 서빙 중. sohobi.net 트래픽 처리. backend URL `sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io` |
| 신규 자원 (`rg-sohobi-prod`) | 모두 Ready, **데이터 0**. PG `sohobi-prod-pg` / Cosmos `sohobi-prod-cosmos` / ACR `sohobiprodacr` / Container App `sohobi-backend` (quickstart placeholder) |
| AI Search | 양쪽 모두 미사용 (구 환경 비활성, 신규 미생성 — PR #339) |
| OpenAI 모델 | 미배포 — quota 재신청 진행 중(외부 의존). chat 서빙 핵심 |
| 자체 RAG (pgvector) | 계획 승인됨 (PR #340). Cutover critical path 외 — 후속 백필 |
| Static Web App | sohobi.net 현재 운영 SWA 그대로 유지 |
| DNS | 가비아 보유 `sohobi.net`, NS는 구 Azure DNS zone에 위임. 현재 백엔드 URL을 SWA 라우팅에서 사용 |

## 1. 확정된 결정 사항

| 항목 | 결정 | 사유 |
|------|------|------|
| DNS 옵션 | **B (NS 위임 유지)** | 옵션 A는 NS 변경 후 24-48h 전파 + 가비아 작업 필요. 옵션 B는 SWA의 backend URL 1줄 변경으로 5분 전환·즉시 롤백 |
| SWA 처리 | **기존 유지** | sohobi.net 무중단 + 신규 생성 인센티브 없음. backend URL 환경변수만 갱신 |
| 점검 윈도우 | KST 새벽 02:00-04:00 권장 | 트래픽 최저 시간대. 실제 일자는 P4 runbook 작성 후 확정 |
| OpenAI quota 미승인 시 | **cutover 지연** | quota 없으면 chat 기능 503 — portfolio 환경에서도 핵심 기능. 승인 후 진행 |
| 자체 RAG (pgvector) | **cutover 후 백필** | backend 코드에 빈 인덱스 fallback 보유. 검색 기능은 cutover 후 별도 phase로 |
| 임베딩 모델 | **`text-embedding-3-large` (3072d) 단일 통합** | 기존 CLAUDE.md 의 legal=small(1536d) / gov=large(3072d) 분리 폐기. pgvector 백필 시 단일 차원 인덱스로 단순화. legal 검색 코드의 1536d 가정 제거는 별 PR (`feat/*-legal-embedding-3072`). cutover 직후 backend 가 large endpoint 만 호출하므로 quota 영향 재확인 필요 |

## 2. PR 분할 + 실행 순서

| # | PR 제목 | 트랙 | 의존 | 추정 |
|---|---------|------|------|------|
| **P0** | 본 문서 (cutover 세부 기획) | meta | 없음 | 즉시 |
| **P1** | scripts/migrate import 3종 (cosmos_import / pg_restore / blob_sync) | A (데이터 이전) | P0 | 0.5d |
| **P2** | `.github/workflows/build-backend-new.yml` (신규 ACR push 워크플로) | B1 | P0 | 0.3d |
| **P3** | Container App env vars + revision Bicep 업데이트 (`useBackendAcrImage=true`, `targetPort=8000`, `livenessProbePath=/health`) | B2+B3 | P2 + ACR에 첫 이미지 적재 | 0.5d |
| **P4** | `docs/runbooks/azure-cutover.md` (D-day 분 단위, P5 SWA URL 갱신 단계 포함) | D1 + D3 | P1 dry-run 실측 후 | 0.5d |

P5(SWA backend URL 환경변수 갱신)는 별도 PR로 분리하지 않고 P4 runbook의 D-day 한 단계로 흡수한다. SWA Portal에서 환경변수 1개 변경 + 캐시 무효화만 필요해 코드 변경이 없다.

**Critical path**: P1 → (dry-run) → P3 → P4 → 윈도우 확정 → D-day.

## 3. 트랙 A — 데이터 이전 파이프라인 (P1)

### A1. `scripts/migrate/06_cosmos_import.py`

- 입력: `scripts/migrate/02_cosmos_export.py` 출력 JSONL (gzip 또는 plain)
- 출력: 신규 Cosmos `sohobi-prod-cosmos` 컨테이너에 upsert
- 인증: AAD `DefaultAzureCredential` (신규 Cosmos는 `disableLocalAuth=true`)
- 핵심 옵션:
  - `--containers sessions,usage_events,feedback,checklist,roadmap_votes,users`
  - `--since <ISO timestamp>` — 증분 import (cutover 마지막 1-2h용)
  - `--dry-run` — 실제 write 없이 row count만 보고
- 멱등: `upsert_item` 사용 (id 충돌 시 덮어쓰기)
- 에러 처리: 각 batch 단위 retry 3회, 실패 시 실패 doc id를 stderr로 dump

### A2. `scripts/migrate/07_pg_restore.sh`

- 입력: `04_pg_dump.sh` 출력 `pg_dump --format=custom` 파일 (`.dump`)
- 출력: 신규 PG `sohobi-prod-pg`에 `pg_restore`
- 인증: env `PG_HOST`/`PG_USER`/`PG_PASSWORD` (신규 PG는 password auth, 추후 AAD 추가)
- 핵심 옵션:
  - `--schema-only` / `--data-only` 분리 실행 가능
  - `--clean --if-exists` 멱등 보장
  - `--jobs 4` 병렬 restore (B1ms 한계 고려해 default는 1)
- 사전 검증: 신규 PG에 `sohobi` DB 존재 확인, 필요 시 extension 활성화 (pgvector는 Track C에서 별도 처리)

### A3. `scripts/migrate/08_blob_sync.sh`

- 입력: 구 Storage `sohobi9638logs` blob container `sohobi-logs`
- 출력: 신규 Storage `sohobiprodlogs` blob container `sohobi-logs`
- 도구: `azcopy sync` (OAuth 인증 + Storage Account 이름 옵션 방식)
- 인자 방식: `--src-account / --src-container / --dst-account / --dst-container` (실제 시그니처)
  - 신규 환경 Storage Account Key 비활성 정책에 따라 SAS URL 발급 대신 `az login` + `azcopy login --auth-mode oauth` 사용
  - 필요 권한: source 에 Storage Blob Data Reader, destination 에 Storage Blob Data Contributor
- 옵션: `--delete-destination=false` (안전), `--recursive=true` (기본 true, `--no-recursive` 로 비활성)
- 구·신 테넌트가 다른 경우 azcopy 토큰이 한 테넌트만 유효하므로 `azcopy login --tenant-id <X>` 로 명시 또는 SAS URL 우회 옵션 추가 검토

### A4. Dry-run 검증

P1 머지 후 1회 실행:
```bash
# 구 환경 컨텍스트 set
az account set --subscription <구 sub>
bash scripts/migrate/04_pg_dump.sh ./backups/pg-$(date +%s).dump
backend/.venv/bin/python3 scripts/migrate/02_cosmos_export.py --out-dir ./backups/cosmos-$(date +%s)/
backend/.venv/bin/python3 scripts/migrate/03_blob_backup.py  # 로컬 백업 (azcopy 미설치 환경 fallback)

# 신규 환경 컨텍스트 set
az account set --subscription eba83124-c3b9-4a07-be43-e0c9acdc3425
bash scripts/migrate/07_pg_restore.sh ./backups/pg-*.dump --jobs 1
backend/.venv/bin/python3 scripts/migrate/06_cosmos_import.py --in ./backups/cosmos-*/
# 08은 dry-run 단계가 아닌 cutover 직전 1회 실행 권장 (구→신 직접 sync)
# bash scripts/migrate/08_blob_sync.sh --src-account sohobi9638logs --dst-account sohobiprodlogs
```
- 측정: 각 단계 wall-clock 시간 + 결과 row count diff
- 산출물: PR 코멘트로 dry-run 보고서 (P4 runbook 작성 input)

## 4. 트랙 B — 실 backend 이미지 배포 (P2 + P3)

### B1. `.github/workflows/build-backend-new.yml` (P2)

기존 [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)은 구 환경(`AZURE_CLIENT_ID` 무 `_B`)을 타겟. 신규 환경용은 별도 워크플로로 분리:

- 트리거: `workflow_dispatch` 수동 (cutover 직전까지 자동 push 금지)
- 입력:
  - `deploy` (choice: true/false, default false) — true 시 build 후 Container App revision update까지 수행
  - `image_tag` (string, optional) — 추가 태그. 정규식 `^[A-Za-z0-9._-]+$` 화이트리스트 검증. D-day 약속 태그: `cutover`
- 인증: OIDC federated (`AZURE_CLIENT_ID_B` / `AZURE_TENANT_ID_B` / `AZURE_SUBSCRIPTION_ID_B`)
- ACR: `sohobiprodacr.azurecr.io`
- 이미지 태그: `sohobi-backend:${{ github.sha }}` + `:latest` + (optional) `inputs.image_tag`
- 단계:
  1. checkout
  2. Azure login (OIDC)
  3. ACR 로그인 (`az acr login --name sohobiprodacr`)
  4. Docker build + push
  5. (deploy=true 시) Container App revision update + provisioningState 검증 게이트

cutover 직후 `deploy-backend.yml`(구)는 비활성화 또는 삭제.

### B2 + B3. Container App env + revision (P3)

- Bicep `infra/bicep/main.bicep` + `modules/container-app.bicep` 수정:
  - 신규 param `useBackendAcrImage` (bool, default false) — `true` 전환 시 ACR 이미지 사용. 외부 노출 param 이름은 `useBackendAcrImage` (내부 module param은 `useAcrImage`로 wrap)
  - `backendImage` (string, default `sohobi-backend:latest`)
  - `targetPort=8000` (toggle=true 시), `targetPort=80` (toggle=false 시 quickstart)
  - `livenessProbePath=/health` (FastAPI 현행 `backend/api_server.py:275`. `/api/v1/...` 는 query endpoint group 별도)
  - `envVars` 배열 (toggle=true 시 inline 주입, 비-민감 endpoint·식별자만):

    ```env
    APP_ENV=production
    AZURE_OPENAI_ENDPOINT=<openai.outputs.endpoint>
    AZURE_OPENAI_API_VERSION=2024-08-01-preview
    AZURE_DEPLOYMENT_NAME=<openai.outputs.chatDeploymentName>          # backend 코드가 실제 읽는 키
    AZURE_OPENAI_CHAT_DEPLOYMENT=<openai.outputs.chatDeploymentName>    # alias (호환성)
    AZURE_EMBEDDING_DEPLOYMENT=<openai.outputs.embeddingLargeDeploymentName>
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<openai.outputs.embeddingLargeDeploymentName>
    AZURE_OPENAI_EMBEDDING_DIMS=3072
    COSMOS_ENDPOINT=https://${namePrefix}-${env}-cosmos.documents.azure.com:443/   # 순환 의존 우회 (하드코딩)
    COSMOS_DATABASE=sohobi                                              # 코드 source-of-truth (NAME suffix 없음)
    PG_HOST=<postgres.outputs.fqdn>
    PG_PORT=5432
    PG_DB=<postgres.outputs.databaseName>
    PG_USER=<postgres.outputs.administratorLogin>
    PG_SSLMODE=require
    VWORLD_DOMAIN=https://sohobi.net
    AZURE_STORAGE_CONTAINER=sohobi-logs
    RAG_BACKEND=disabled                                                # cutover 후 pgvector 백필 전까지
    ```

  - 결정 사항 (B2+B3 한정):
    - **임베딩 통합**: 신규 환경은 `text-embedding-3-large` (3072d) 단일로 통합. CLAUDE.md 가 명시한 legal=small(1536d) / gov=large(3072d) 분리는 폐기 예정. legal 검색 코드의 1536d 가정은 별 PR(`feat/*-legal-embedding-3072`) 로 제거 필요.
    - **COSMOS_ENDPOINT 하드코딩**: `cosmos.outputs.endpoint` 참조 시 backendApp ↔ cosmos 순환 의존(cosmos가 backendApp.principalId 의존)이 발생하므로 결정적 naming 기반 static URL 우회. 향후 module 분리(`cosmos-roles.bicep`)로 순환 끊기 검토.
    - **alias 이중 주입**: 코드가 읽는 키(`AZURE_DEPLOYMENT_NAME`)와 신규 컨벤션 키(`AZURE_OPENAI_CHAT_DEPLOYMENT`)를 모두 주입. 코드 정리 후 alias 제거.
    - **`COSMOS_DATABASE_NAME` 표기 금지**: 백엔드 코드는 `COSMOS_DATABASE` (suffix 없음) 만 읽음 (`backend/session_store.py:46`, `backend/roadmap_router.py:225` 등). 현재 `infra/bicep/main.bicep` 의 `COSMOS_DATABASE_NAME` 주입은 후속 PR에서 `COSMOS_DATABASE` 로 정정 필요. (default 값 `sohobi` 가 우연히 일치해 silent OK 중)
  - 민감 값 분리 주입 (P3 Bicep 미포함, P4 runbook T+0:35 단계):
    - `PG_PASSWORD`, `AZURE_OPENAI_API_KEY`, `API_SECRET_KEY`, `EXPORT_SECRET`, JWT secret 등은 `az containerapp secret set ...` + `az containerapp update --set-env-vars KEY=secretref:...` 으로 별도 처리
    - Bicep redeploy 시 이 envVars 가 덮일 수 있으므로 runbook 에 머지 규칙 주석 필요

### B4. (외부 의존) OpenAI quota 승인 후

quota 승인되면 별도 PR로:
- `openaiDeployModels=true` Bicep 토글
- `AZURE_OPENAI_API_KEY` Container App secret 추가
- backend 이미지 재배포 또는 revision restart

## 5. 트랙 D — runbook + 라우팅 (P4, P5 흡수)

### D1. `docs/runbooks/azure-cutover.md` (P4)

분 단위 절차서. 골격:

```
T-1d: 점검 공지 (사용자에게)
T-2h: 사전 backup 실행 (Track A 풀 셋)
T-0h: 윈도우 시작
  T+0~5: 구 backend rate limit / drain
  T+5~10: 구 환경 freeze (구 Container App stop)
  T+10~30: 마지막 증분 데이터 이전 (Track A 증분)
  T+30~45: 신규 backend revision activate (P3 결과)
  T+45~60: smoke test (5 시나리오)
  T+60~75: SWA backend URL 변경 (P5)
  T+75~90: 모니터링 + 503 → 200 회복 확인
T+24h: 사후 보고 + 구 환경 정리 결정
롤백 트리거 + 절차
```

### D3. SWA backend URL 변경 (P4 runbook 흡수, 별 PR 없음)

기존 SWA의 환경변수 또는 API 라우팅 설정에서 backend 도메인을 구→신으로 변경:
- 현재: `sohobi-backend.livelybay-...koreacentralapps.io`
- 신규: `sohobi-backend.<신규env-suffix>.koreacentral.azurecontainerapps.io`

신규 backend FQDN은 P3 머지 후 az CLI로 동적 조회 (Bicep `COSMOS_ENDPOINT` 와 달리 ingress FQDN은 module output 의존 없음):
```bash
az containerapp show -g rg-sohobi-prod -n sohobi-backend --query properties.configuration.ingress.fqdn -o tsv
```

cutover D-day T+1:15 단계에서 SWA Portal 또는 `az staticwebapp appsettings set` 으로 수행. SWA 환경변수 변경은 코드 변경이 없으므로 별 PR 없이 runbook 한 단계로 흡수.

## 6. 위험 + 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| 신규 PG B1ms restore 시간 초과 (sangkwon 50만+ 행) | 윈도우 초과 | dry-run 실측 → 윈도우 늘리거나 사전 적재 후 증분만 |
| Cosmos TTL 24h 컨테이너 마지막 export 누락 | 일부 세션 유실 | T+5~10 freeze 즉시 마지막 export. dry-run에서 검증 |
| OpenAI quota 미승인 상태 cutover | chat 503 (핵심 기능 미작동) | cutover 연기. 또는 구 OpenAI 키 임시 잔류 (이중 인증 env) |
| 신규 backend 첫 부트스트랩 timeout 22분 (handoff §traps) | 윈도우 초과 | P3 머지 후 cutover 전 1회 사전 deploy로 `useBackendAcrImage=true` 검증 |
| SWA 환경변수 변경 후 캐시 지연 | 일부 사용자 5-10분 503 | 사전 SWA 설정 검토. CloudFlare 등 CDN 캐시 키 확인 (현재 SWA만 사용 시 무관) |
| 신규 PG password auth → cutover 후 AAD 전환 | 보안 timeline | cutover 후 별도 PR로 AAD 추가 (password auth 유지하면서 점진 전환) |

### 6.1 데이터 단계별 실패 복구 절차

cutover 중 데이터 이전 일부가 실패한 경우 신규 환경을 깨끗한 상태로 되돌리고 재시도하는 절차:

| 단계 | 부분 실패 시 복구 |
|------|------------------|
| PG restore 중 (07_pg_restore.sh) | 신규 PG 초기화: `psql -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'` 후 `pg_restore --exit-on-error` 로 재시도. `--clean --if-exists` 의 무방비 DROP 방지를 위해 운영자는 항상 `--list` 로 dump 내용 사전 확인 |
| Cosmos import 중 (06_cosmos_import.py) | `upsert_item` 멱등이므로 단순 재실행 안전. 단 `--since` ISO timestamp 를 직전 실패 시점 직전으로 좁혀 중복 트래픽 최소화. failures-*.jsonl 파일이 있으면 해당 id 만 재처리 |
| Blob sync 중 (08_blob_sync.sh) | `--delete-destination=false` 기본이라 재실행 안전. azcopy summary 의 Failed 카운트가 0인지 확인 후 통과 |
| Container App revision activate timeout (22분) | 즉시 이전 healthy revision 으로 traffic 100% 복귀: `az containerapp revision set-mode --mode single -g rg-sohobi-prod -n sohobi-backend` + 이전 revision activate. 신규 revision 은 별도 `revision deactivate` 후 image / env 수정 후 재시도 |
| 신규 환경 전체 롤백 (마지막 수단) | SWA backend URL 을 구 backend FQDN 으로 즉시 복귀 + 구 Container App revision 활성화 유지 (구 환경은 cool-down 7~14일 살아 있음) |

## 7. 검증 (D-day 종료 후)

1. **데이터 일관성**: `SELECT count(*) FROM sangkwon_sales;` (구·신 일치), Cosmos 컨테이너별 row count diff
2. **E2E TC** (CLAUDE.md 표준 루틴):
   - `/api/v1/query` 5 시나리오 (admin/finance/legal/location/chat)
   - 세션 생성·재호출 (Cosmos sessions)
   - 위치 에이전트 PG read
   - 로그 신규 Blob append
   - AI Search 빈 인덱스 fallback (검색 도메인)
3. **모니터링**: 24h 동안 5xx rate, 응답시간 P95, Container App replica 추이 관찰
4. **롤백 트리거**: 5xx rate > 5% 5분 지속 시 또는 핵심 기능 실패 시 SWA backend URL 즉시 복귀

## 8. cutover 후 정리 작업

- 구 환경 (`rg-ejp-9638`) **즉시 삭제 금지** — 7-14일 cool-down 후 stakeholder 확인 후 삭제
- 구 OpenAI 키 비활성화 (신규 키로 전환 완료 확인 후)
- `deploy-backend.yml` (구 워크플로) 삭제 또는 disable
- `backend/.env`의 `BACKEND_HOST`, OpenAI/Search/PG endpoint 모두 신규로 갱신
- 자체 RAG (pgvector) Phase A·B·C 본격 착수 — cutover와 분리된 별 PR 시퀀스

## 9. 다음 액션

P0 머지 후 즉시 **P1(import 스크립트 3종)** 착수. P1 머지 후 dry-run 실행해 실측 시간 수집 → P4 runbook 작성. 병렬로 P2(build workflow) 작업 가능.

**사용자 결정 잔여 사항**: 점검 윈도우 일자(주말 OR 평일 새벽). 나머지 결정은 §1에 확정.
