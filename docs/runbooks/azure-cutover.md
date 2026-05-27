# Azure 신규 테넌트 cutover Runbook

> D-day 분 단위 절차서. 단일 점검 윈도우(60-120분) 내 라이브 서비스를 구 환경(`rg-ejp-9638`, 별도 테넌트) → 신규 환경(`rg-sohobi-prod`, sub `eba83124-...`, tenant `5555704e-...`)으로 전환.
>
> **본 runbook을 처음부터 끝까지 읽고 시작하라.** 단계 건너뛰지 말 것. 실수 시 §롤백 절차 즉시 적용.
>
> 관련: [`docs/plans/2026-04-30-cutover-detailed-plan.md`](../plans/2026-04-30-cutover-detailed-plan.md)

## 전제 조건 (D-day 24h 전 점검)

- [ ] PR #335 (PG B1ms) / #336 (OpenAI account) / #337 (PG nightly cron) / #339 (AI Search 차단) / #340 (RAG plan) / **#349 (cutover 기획)** / **#350 (import 스크립트)** / **#351 (build workflow)** / **#352 (Container App config)** 모두 머지 완료
- [ ] OpenAI `gpt-5.4-mini` GlobalStandard quota 승인 완료 (60K TPM). 미승인 시 cutover 연기
- [ ] OpenAI 모델 배포 완료 — `openaiDeployModels=true` Bicep 재배포 + `az cognitiveservices account deployment list` 확인
- [ ] 구 환경 OpenAI API key + Search key + Cosmos key + Blob connection string 모두 보유 (구 sub `az` 컨텍스트에서 추출)
- [ ] 신규 환경 OpenAI API key 발급 + 별도 보관 (`az cognitiveservices account keys list -g rg-sohobi-prod -n sohobi-prod-openai`)
- [ ] **사전 dump+import dry-run 1회 완료** — PG/Cosmos/Blob 전량 데이터 사전 적재 + row count 일치 확인
- [ ] `build-backend-new.yml` workflow_dispatch로 신규 backend 이미지 ACR에 push 완료 (deploy=false로 build만)
- [ ] P3 `useBackendAcrImage=true` Bicep 사전 deploy 완료 → Container App revision 첫 부트스트랩 검증 (handoff §traps — 22분 timeout 우회 확인)
- [ ] 점검 공지 게시: KST 점검 시각 1일 전 sohobi.net 공지 + Slack/이메일
- [ ] 롤백 트리거 + 절차 숙지 (§롤백)

## D-day 시각표 (KST 02:00 기준 — 새벽 트래픽 최저)

다음 시간은 KST 02:00을 T+0:00으로 가정. 다른 시각 잡았으면 동일 offset 적용.

### T-2:00 (00:00 KST) — 사전 backup 마지막 실행

```bash
# 구 sub 컨텍스트
az account set --subscription <구-sub-id>

# 1) Cosmos 전량 export
backend/.venv/bin/python3 scripts/migrate/02_cosmos_export.py

# 2) PG 전량 dump
bash scripts/migrate/04_pg_dump.sh

# 3) Blob 전량 sync
bash scripts/migrate/08_blob_sync.sh --src-account sohobi9638logs --dst-account sohobiprodlogs

# 산출물 확인: backups/cosmos/<ts>/ + backups/pg/<ts>/ + backups/blob-sync/<ts>/
ls -la backups/
```

성공 조건: 모든 스크립트 exit 0 + 산출물 디렉토리에 summary 파일 존재.

### T-0:30 (01:30 KST) — 신규 환경에 사전 데이터 적재

```bash
# 신규 sub 컨텍스트
az account set --subscription eba83124-c3b9-4a07-be43-e0c9acdc3425

# 신규 환경 PG/Cosmos credentials로 backend/.env 임시 갱신 (cutover 종료 후 정식 변경)
cp backend/.env backend/.env.cutover-backup
# PG_HOST=sohobi-prod-pg.postgres.database.azure.com, PG_USER=sohobiadmin, COSMOS_ENDPOINT=신규 등으로 수정

# 1) PG restore (병렬 1, 첫 실행은 시간 측정)
bash scripts/migrate/07_pg_restore.sh backups/pg/<ts>/sohobi.dump --jobs 1
# 종료 후: backups/pg-restore/<ts>/row_counts.tsv 확인

# 2) Cosmos import
backend/.venv/bin/python3 scripts/migrate/06_cosmos_import.py --in backups/cosmos/<ts>/

# 3) Blob sync (이미 T-2:00에 한 번 했으면 증분만)
bash scripts/migrate/08_blob_sync.sh --src-account sohobi9638logs --dst-account sohobiprodlogs
```

성공 조건: row count diff < 1% (cutover 마지막 증분에서 0으로 수렴 예정).

### T+0:00 (02:00 KST) — 윈도우 시작

```
[1] sohobi.net 503 공지 페이지 노출 (가능하면) — SWA route 일시 redirect
[2] Slack/이메일 알림 — "점검 시작, 예상 60-120분"
```

### T+0:05 — 구 환경 freeze

```bash
# 구 sub 컨텍스트
az account set --subscription <구-sub-id>

# 구 Container App 정지 — backend가 새로운 쓰기 받지 않도록
az containerapp revision deactivate \
  -g rg-ejp-9638 -n <구-backend-name> \
  --revision $(az containerapp show -g rg-ejp-9638 -n <구-backend-name> --query "properties.latestRevisionName" -o tsv)

# 또는 Container App 자체를 stop (가능 시):
# az containerapp stop -g rg-ejp-9638 -n <구-backend-name>
```

성공 조건: 구 backend에 `curl` 시 5xx 또는 connection refused.

### T+0:10 — 마지막 증분 데이터 이전

```bash
# 구 sub 컨텍스트로 마지막 export
az account set --subscription <구-sub-id>

# Cosmos: --since 마지막 export 시각 (T-2:00의 ts 사용)
backend/.venv/bin/python3 scripts/migrate/02_cosmos_export.py \
  --since 2026-MM-DDTHH:MM:SSZ  # T-2:00 시각 (UTC)

# PG: 위치 데이터 정적이라 사전 dump로 사실상 충분. 안전을 위해 재dump
bash scripts/migrate/04_pg_dump.sh

# Blob: 마지막 sync (delete-destination=false 유지)
bash scripts/migrate/08_blob_sync.sh --src-account sohobi9638logs --dst-account sohobiprodlogs

# 신규 sub 컨텍스트로 마지막 import
az account set --subscription eba83124-c3b9-4a07-be43-e0c9acdc3425

backend/.venv/bin/python3 scripts/migrate/06_cosmos_import.py --in backups/cosmos/<신규-ts>/
bash scripts/migrate/07_pg_restore.sh backups/pg/<신규-ts>/sohobi.dump --clean --jobs 1
```

성공 조건: row count diff = 0 (구·신 일치).

### T+0:35 — 신규 backend 활성화

```bash
az account set --subscription eba83124-c3b9-4a07-be43-e0c9acdc3425

# 1) Container App secrets 일괄 주입 (민감 env)
az containerapp secret set -g rg-sohobi-prod -n sohobi-backend --secrets \
  azure-openai-api-key=<신규 OpenAI key> \
  pg-password=<PG_ADMIN_PASSWORD 값 — Bicep 배포 시 사용한 값> \
  jwt-secret=<기존 JWT_SECRET 또는 신규 발급> \
  api-secret-key=<기존 API_SECRET_KEY 또는 신규 발급> \
  export-secret=<기존 EXPORT_SECRET 또는 신규 발급> \
  azure-storage-connection-string=<신규 Storage connection string> \
  oracle-password=<기존 Oracle password> \
  seoul-api-key=<...> vworld-api-key=<...> kakao-rest-key=<...> kto-gw-info-key=<...> \
  gov24-api-key=<...> kstartup-api-key=<...> kised-space-api-key=<...> kised-agency-api-key=<...> \
  kised-edu-api-key=<...> sme24-api-key=<...> bizinfo-api-key=<...>

# 2) env-var와 secret 매핑
az containerapp update -g rg-sohobi-prod -n sohobi-backend --set-env-vars \
  "AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key" \
  "PG_PASSWORD=secretref:pg-password" \
  "JWT_SECRET=secretref:jwt-secret" \
  "API_SECRET_KEY=secretref:api-secret-key" \
  "EXPORT_SECRET=secretref:export-secret" \
  "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-storage-connection-string" \
  "ORACLE_PASSWORD=secretref:oracle-password" \
  "SEOUL_API_KEY=secretref:seoul-api-key" \
  "VWORLD_API_KEY=secretref:vworld-api-key" \
  "KAKAO_REST_KEY=secretref:kakao-rest-key" \
  "KTO_GW_INFO_KEY=secretref:kto-gw-info-key" \
  "GOV24_API_KEY=secretref:gov24-api-key" \
  "KSTARTUP_API_KEY=secretref:kstartup-api-key" \
  "KISED_SPACE_API_KEY=secretref:kised-space-api-key" \
  "KISED_AGENCY_API_KEY=secretref:kised-agency-api-key" \
  "KISED_EDU_API_KEY=secretref:kised-edu-api-key" \
  "SME24_API_KEY=secretref:sme24-api-key" \
  "BIZINFO_API_KEY=secretref:bizinfo-api-key" \
  "ORACLE_USER=shobi" "ORACLE_HOST=10.1.92.119" "ORACLE_PORT=1521" "ORACLE_SID=xe"

# 3) revision 생성 (latest 이미지로)
gh workflow run build-backend-new.yml -f deploy=true -f image_tag=cutover

# 또는 az containerapp update --image 직접
```

성공 조건: `az containerapp revision list` 새 revision Provisioning → Healthy.

### T+0:55 — E2E smoke test (5 시나리오)

신규 backend FQDN: `az containerapp show -g rg-sohobi-prod -n sohobi-backend --query properties.configuration.ingress.fqdn -o tsv`

```bash
NEW_BACKEND_HOST="https://<신규 fqdn>"

# 1) Health
curl -sf "$NEW_BACKEND_HOST/health" | jq .

# 2) admin 도메인 (rate limit·auth 통과 확인용 API 키 필요)
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_SECRET_KEY>" \
  -d '{"question": "소상공인 정부 지원 받을 수 있나요"}'

# 3) finance 도메인
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" -H "X-API-Key: <key>" \
  -d '{"question": "월 매출 1000만원 카페 손익 시뮬레이션"}'

# 4) legal — 빈 인덱스 fallback 확인
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" -H "X-API-Key: <key>" \
  -d '{"question": "식품위생법 위반 시 처벌"}'

# 5) location — PG read
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" -H "X-API-Key: <key>" \
  -d '{"question": "강남역 카페 상권"}'

# 6) chat — 일반 대화
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" -H "X-API-Key: <key>" \
  -d '{"question": "안녕하세요"}'
```

성공 조건: 6건 모두 HTTP 200, 응답 JSON에 `answer` 필드 존재.

**실패 시 즉시 §롤백.**

### T+1:15 — SWA backend URL 변경

기존 SWA(`sohobi.net`)의 backend API endpoint를 구 → 신으로 변경.

옵션 1: SWA `staticwebapp.config.json` 또는 환경변수 — 코드 commit + 자동 deploy
옵션 2: Azure Portal에서 SWA "Configuration" 직접 수정

```bash
# 신규 backend FQDN 확인
NEW_FQDN=$(az containerapp show -g rg-sohobi-prod -n sohobi-backend --query properties.configuration.ingress.fqdn -o tsv)
echo "신규 backend FQDN: $NEW_FQDN"

# SWA 설정 변경 (방법은 SWA 운영 상황 따라):
# - GitHub Actions deploy 트리거: frontend/.env.production의 VITE_BACKEND_URL 변경 + commit
# - 또는 az staticwebapp appsettings set ...
```

성공 조건: `curl https://sohobi.net/api/v1/query` (실제 SWA가 backend로 proxy하는 path) 응답 정상.

### T+1:30 — 모니터링 + 윈도우 종료

```bash
# 신규 backend 응답시간·5xx rate 모니터링 (15분 관찰)
watch -n 30 "curl -sf -w 'HTTP %{http_code} / %{time_total}s\n' -o /dev/null https://sohobi.net/health"

# Container App replica count 추이
watch -n 30 "az containerapp replica list -g rg-sohobi-prod -n sohobi-backend --query '[].name' -o tsv | wc -l"

# 로그 확인 (신규 backend `/api/v1/logs` 경로 — EXPORT_SECRET 필요)
curl -s "https://sohobi.net/api/v1/logs?type=queries&limit=20" -H "X-Export-Secret: <EXPORT_SECRET>"
```

성공 조건: 15분 동안 5xx rate < 1%, 응답시간 P95 < 3s.

**모두 충족 시 cutover 종료.** Slack/이메일에 "점검 완료" 알림.

## 롤백 절차 (모든 단계에서 적용 가능)

조건:
- E2E smoke test 6건 중 2건 이상 실패
- 5xx rate > 5% 5분 지속
- 핵심 데이터 불일치 (row count diff > 5%)

```bash
# 1) SWA backend URL을 구 환경으로 복귀 (변경했다면)
# - frontend/.env.production revert + redeploy

# 2) 구 Container App revision 재활성화
az account set --subscription <구-sub-id>
az containerapp revision activate \
  -g rg-ejp-9638 -n <구-backend-name> \
  --revision <freeze 시 deactivate한 revision name>

# 3) 신규 환경은 그대로 두고 (자원 비용은 ContainerApps idle = 0)
#    다음 cutover 시도 시 재사용

# 4) Slack/이메일: "점검 중단, 구 환경 복귀. 다음 시도 일정 별도 안내"
```

롤백 후: post-mortem 작성. 재시도는 최소 7일 후 (재발 방지책 적용 후).

## D+1 (cutover 24h 후) — 사후 검증

- [ ] 신규 backend 24h 5xx rate · 응답시간 보고서
- [ ] 사용자 문의 0건 또는 알려진 이슈만 (`feedback` Cosmos 컨테이너 모니터링)
- [ ] PG nightly cron(PR #337) 정상 동작 확인
- [ ] 신규 자원 청구 정상 (Cost Management MTD query)
- [ ] **구 환경 자원은 즉시 삭제 금지** — 7-14일 cool-down 후 stakeholder 확인 후 삭제 결정

## D+7 ~ D+14 — 구 환경 정리

- [ ] `deploy-backend.yml` 워크플로 삭제 또는 disable
- [ ] 구 OpenAI API key 비활성화
- [ ] 구 Storage SAS·키 회수
- [ ] 구 RG `rg-ejp-9638` 자원 단계적 삭제 (Container App → ACR → PG → Cosmos → Storage 순)
- [ ] CLAUDE.md / docs 갱신 — `BACKEND_HOST` 등 신규로 영구 변경

## 참고

- 신규 자원 인벤토리: §0 "전제 조건" + `az resource list -g rg-sohobi-prod`
- 환경 변수 매핑: [backend/.env.example](../../backend/.env.example)
- 자체 RAG 전환 (cutover 후 별도 시퀀스): [docs/plans/strategic/self-hosted-rag-and-db-cost-optimization.md](../plans/strategic/self-hosted-rag-and-db-cost-optimization.md)
