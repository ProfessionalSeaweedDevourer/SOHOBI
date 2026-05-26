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

## 2. PR 분할 + 실행 순서

| # | PR 제목 | 트랙 | 의존 | 추정 |
|---|---------|------|------|------|
| **P0** | 본 문서 (cutover 세부 기획) | meta | 없음 | 즉시 |
| **P1** | scripts/migrate import 3종 (cosmos_import / pg_restore / blob_sync) | A (데이터 이전) | P0 | 0.5d |
| **P2** | `.github/workflows/build-backend-new.yml` (신규 ACR push 워크플로) | B1 | P0 | 0.3d |
| **P3** | Container App env vars + revision Bicep 업데이트 (`useAcrImage=true`, `targetPort=8000`, `livenessProbePath`) | B2+B3 | P2 + ACR에 첫 이미지 적재 | 0.5d |
| **P4** | `docs/runbooks/azure-cutover.md` (D-day 분 단위) | D1 | P1 dry-run 실측 후 | 0.5d |
| **P5** | SWA backend URL 환경변수 갱신 (cutover 직전 또는 D-day 중 수행) | D3 | P3 | 0.1d |

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
- 도구: `azcopy sync` (SAS URL 두 개 인자)
- 옵션: `--delete-destination=false` (안전), `--recursive=true`
- 사전 사용: SAS URL 발급 스크립트 추가 (Storage Account Key는 신규에선 비활성, key가 없으면 OAuth 토큰 + `azcopy login`)

### A4. Dry-run 검증

P1 머지 후 1회 실행:
```bash
# 구 환경 컨텍스트 set
az account set --subscription <구 sub>
bash scripts/migrate/04_pg_dump.sh ./backups/pg-$(date +%s).dump
python scripts/migrate/02_cosmos_export.py --out ./backups/cosmos-$(date +%s)/
bash scripts/migrate/03_blob_backup.py ./backups/blob-$(date +%s)/

# 신규 환경 컨텍스트 set
az account set --subscription eba83124-c3b9-4a07-be43-e0c9acdc3425
bash scripts/migrate/07_pg_restore.sh ./backups/pg-*.dump --jobs 1
python scripts/migrate/06_cosmos_import.py --in ./backups/cosmos-*/
bash scripts/migrate/08_blob_sync.sh
```
- 측정: 각 단계 wall-clock 시간 + 결과 row count diff
- 산출물: PR 코멘트로 dry-run 보고서 (P4 runbook 작성 input)

## 4. 트랙 B — 실 backend 이미지 배포 (P2 + P3)

### B1. `.github/workflows/build-backend-new.yml` (P2)

기존 [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)은 구 환경(`AZURE_CLIENT_ID` 무 `_B`)을 타겟. 신규 환경용은 별도 워크플로로 분리:

- 트리거: `workflow_dispatch` 수동 (cutover 직전까지 자동 push 금지)
- 인증: `AZURE_CLIENT_ID_B` / `AZURE_TENANT_ID_B` / `AZURE_SUBSCRIPTION_ID_B`
- ACR: `sohobiprodacr.azurecr.io`
- 이미지 태그: `sohobi-backend:${{ github.sha }}` + `:latest`
- 단계:
  1. checkout
  2. Azure login (OIDC)
  3. ACR 로그인 (`az acr login --name sohobiprodacr`)
  4. Docker build + push
  5. (선택) Container App revision update — P3 머지 후 활성화. cutover 직전엔 build만, deploy는 manual.

cutover 직후 `deploy-backend.yml`(구)는 비활성화 또는 삭제.

### B2 + B3. Container App env + revision (P3)

- Bicep `modules/container-app.bicep` 수정:
  - `useAcrImage=true` 활성화
  - `targetPort=8000`
  - `livenessProbePath=/api/v1/health` (실제 backend는 이 path가 있어야 함 — 확인 필요)
  - `envVars` 배열에 신규 endpoint 주입:
    - `PG_HOST=sohobi-prod-pg.postgres.database.azure.com`
    - `PG_DB=sohobi`, `PG_USER=sohobiadmin`, `PG_PASSWORD` (secretRef)
    - `COSMOS_ENDPOINT=https://sohobi-prod-cosmos.documents.azure.com:443/`
    - `AZURE_OPENAI_ENDPOINT=https://sohobi-prod-openai.openai.azure.com/`
    - `AZURE_OPENAI_API_KEY` (secretRef) — quota 승인 후 추가
    - 검색 관련 env는 **비활성** (RAG_BACKEND=disabled or fallback) — pgvector 백필 전까지
- Container App secrets: PG_PASSWORD, AZURE_OPENAI_API_KEY 등은 `secretRef`로 주입 (Container App secrets store)
- 첫 이미지 적재 후 manual revision activate

### B4. (외부 의존) OpenAI quota 승인 후

quota 승인되면 별도 PR로:
- `openaiDeployModels=true` Bicep 토글
- `AZURE_OPENAI_API_KEY` Container App secret 추가
- backend 이미지 재배포 또는 revision restart

## 5. 트랙 D — runbook + 라우팅 (P4 + P5)

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

### D3. SWA backend URL 변경 (P5)

기존 SWA의 환경변수 또는 API 라우팅 설정에서 backend 도메인을 구→신으로 변경:
- 현재: `sohobi-backend.livelybay-...koreacentralapps.io`
- 신규: `sohobi-backend.<신규env-suffix>.koreacentral.azurecontainerapps.io`

신규 backend FQDN은 P3 머지 후 az CLI로 확인:
```bash
az containerapp show -g rg-sohobi-prod -n sohobi-backend --query properties.configuration.ingress.fqdn -o tsv
```

cutover D-day T+60~75 단계에서 수행. PR로 분리 가능하나 manual 작업으로 처리해도 무방 (간단함).

## 6. 위험 + 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| 신규 PG B1ms restore 시간 초과 (sangkwon 50만+ 행) | 윈도우 초과 | dry-run 실측 → 윈도우 늘리거나 사전 적재 후 증분만 |
| Cosmos TTL 24h 컨테이너 마지막 export 누락 | 일부 세션 유실 | T+5~10 freeze 즉시 마지막 export. dry-run에서 검증 |
| OpenAI quota 미승인 상태 cutover | chat 503 (핵심 기능 미작동) | cutover 연기. 또는 구 OpenAI 키 임시 잔류 (이중 인증 env) |
| 신규 backend 첫 부트스트랩 timeout 22분 (handoff §traps) | 윈도우 초과 | P3 머지 후 cutover 전 1회 사전 deploy로 `useAcrImage=true` 검증 |
| SWA 환경변수 변경 후 캐시 지연 | 일부 사용자 5-10분 503 | 사전 SWA 설정 검토. CloudFlare 등 CDN 캐시 키 확인 (현재 SWA만 사용 시 무관) |
| 신규 PG password auth → cutover 후 AAD 전환 | 보안 timeline | cutover 후 별도 PR로 AAD 추가 (password auth 유지하면서 점진 전환) |

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
