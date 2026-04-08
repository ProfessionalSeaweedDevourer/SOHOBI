# SOHOBI 백엔드 보안 강화 계획 — 프로덕션 적용

## Context

코드 레벨 보안 조치(CORS·auth.py·IP 미들웨어·SWA 프록시 코드)는 PR #55로 이미 완료되었다.
이제 프로덕션 환경(Azure Container Apps + Azure SWA + GitHub)에 실제로 활성화하는 단계이다.

**핵심 아키텍처 발견사항 (탐색 결과):**
- GitHub workflow 26번 줄: `VITE_API_URL` 이 Container Apps URL로 **하드코딩** → 빌드 번들에 노출
- `frontend/.env.production`: `VITE_API_URL`, `VITE_MAP_URL`, `VITE_REALESTATE_URL` 세 개 모두 Container Apps URL 직접 기재 (git에 커밋됨)
- `MapView.jsx`가 `VITE_MAP_URL`(`/map/*`)·`VITE_REALESTATE_URL`(`/realestate/*`) 사용 → staticwebapp.config.json에 해당 프록시 규칙 추가 필요
- **FastAPI IP 미들웨어(`ALLOWED_IPS`) 한계:** SWA가 프록시하면 Container Apps는 `X-Forwarded-For`에서 브라우저 IP를 본다(SWA IP가 아님). 따라서 Container Apps **인그레스 수준 IP 제한**(인프라)만 유효하고, `ALLOWED_IPS` 환경변수는 프로덕션에서 비워둔다.

---

## Azure 리소스 식별 정보

| 리소스 | 이름 | 리소스 그룹 |
|--------|------|-------------|
| Container Apps | `sohobi-backend` | `<RESOURCE_GROUP>` |
| Static Web Apps | `<SWA_RESOURCE_NAME>` | `<RESOURCE_GROUP>` |
| Subscription | `<AZURE_SUBSCRIPTION_ID>` | — |

---

## 프로덕션 적용 계획 (Zero-Downtime 순서)

### Phase 1 — GitHub Secrets 등록 (코드 배포 전 선행)

인증이 활성화되기 *전에* 프론트엔드가 키를 갖고 있어야 한다. 순서가 반대면 일시적 401 발생.

```bash
# 1-1. API Key 생성 (터미널에서 실행, 값을 메모해둘 것)
API_KEY=$(openssl rand -hex 32)
echo "생성된 키: $API_KEY"

# 1-2. GitHub Secret 등록
gh secret set VITE_API_KEY --body "$API_KEY" --repo ProfessionalSeaweedDevourer/SOHOBI

# 1-3. 지도 API URL 시크릿을 빈 문자열로 교체 (SWA 프록시 경유로 전환)
gh secret set VITE_MAP_URL --body "" --repo ProfessionalSeaweedDevourer/SOHOBI
gh secret set VITE_REALESTATE_URL --body "" --repo ProfessionalSeaweedDevourer/SOHOBI
```

---

### Phase 2 — 코드 변경 3개 (커밋 → SWA 자동 재빌드)

**변경 파일 1:** `.github/workflows/azure-static-web-apps-<SWA_RESOURCE_NAME>.yml`

- 26번 줄: `VITE_API_URL: https://sohobi-backend...` → `VITE_API_URL: ""`
- env 블록에 추가: `VITE_API_KEY: ${{ secrets.VITE_API_KEY }}`

**변경 파일 2:** `frontend/.env.production`

세 줄 모두 URL을 제거 (빈 값 = SWA 프록시 상대경로 사용):
```
VITE_API_URL=
VITE_MAP_URL=
VITE_REALESTATE_URL=
```

**변경 파일 3:** `frontend/staticwebapp.config.json`

`/map/*`·`/realestate/*` 프록시 규칙 추가 (`MapView.jsx`가 사용):
```json
{
  "routes": [
    { "route": "/api/*",        "rewrite": "https://sohobi-backend...azurecontainerapps.io/api/*" },
    { "route": "/map/*",        "rewrite": "https://sohobi-backend...azurecontainerapps.io/map/*" },
    { "route": "/realestate/*", "rewrite": "https://sohobi-backend...azurecontainerapps.io/realestate/*" }
  ]
}
```

→ **PARK 브랜치에 커밋 + push → PR #55에 추가 커밋 or 새 PR**
→ main 머지 시 SWA GitHub Actions가 자동으로 재빌드·배포

---

### Phase 3 — SWA 재빌드 완료 확인

```bash
gh run list --workflow="azure-static-web-apps-<SWA_RESOURCE_NAME>.yml" \
  --repo ProfessionalSeaweedDevourer/SOHOBI --limit 3
# "completed / success" 확인 후 다음 단계 진행

# sohobi.net 정상 동작 여부 확인
curl -s https://sohobi.net | head -5
```

---

### Phase 4 — Container Apps API Key 활성화 (SWA 배포 완료 후)

이 시점에 Container Apps에 `API_SECRET_KEY`를 설정하면 인증이 즉시 활성화된다.
프론트엔드는 Phase 2에서 이미 `VITE_API_KEY`를 갖고 있으므로 서비스 중단 없음.

```bash
# API_KEY는 Phase 1에서 생성한 값
az containerapp update \
  --name sohobi-backend \
  --resource-group <RESOURCE_GROUP> \
  --set-env-vars \
    "API_SECRET_KEY=$API_KEY" \
    "CORS_EXTRA_ORIGINS="

# 즉시 검증: 인증 없이 직접 호출 → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST <BACKEND_HOST>/api/v1/query \
  -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 401

# sohobi.net 경유 정상 동작 확인
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://sohobi.net/api/v1/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" -d '{"question":"테스트"}'
# 기대: 200
```

---

### Phase 5 — Container Apps 인그레스 IP 제한 (인프라 레벨)

FastAPI `ALLOWED_IPS` 미들웨어는 SWA 프록시 환경에서 정확히 동작하지 않으므로 비워둔다.
인프라 레벨(Container Apps 인그레스)만 사용한다.

```bash
# SWA 아웃바운드 IP 목록 조회
az staticwebapp show \
  --name <SWA_RESOURCE_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --query "properties.outboundIpAddresses" -o tsv
# 출력 예: 20.196.x.x,20.196.y.y,...

# 각 IP마다 허용 규칙 추가 (IP가 여러 개면 반복)
az containerapp ingress access-restriction set \
  --name sohobi-backend \
  --resource-group <RESOURCE_GROUP> \
  --rule-name "allow-swa-1" \
  --ip-address <SWA_IP_1>/32 \
  --action Allow

# 추가적으로 개발팀 공인 IP도 등록 (로컬 테스트용)
# curl ifconfig.me  ← 현재 내 공인 IP 확인
az containerapp ingress access-restriction set \
  --name sohobi-backend \
  --resource-group <RESOURCE_GROUP> \
  --rule-name "allow-dev" \
  --ip-address <내_공인_IP>/32 \
  --action Allow
```

---

## 수정 파일 요약

| 파일 | 변경 내용 | 방식 |
|------|-----------|------|
| `.github/workflows/azure-static-web-apps-*.yml` | `VITE_API_URL=""`, `VITE_API_KEY` 추가 | 코드 커밋 |
| `frontend/.env.production` | 세 URL 모두 비움 | 코드 커밋 |
| `frontend/staticwebapp.config.json` | `/map/*`, `/realestate/*` 프록시 규칙 추가 | 코드 커밋 |
| Container Apps 환경변수 | `API_SECRET_KEY` 설정 | Azure CLI |
| Container Apps 인그레스 | SWA 아웃바운드 IP 화이트리스트 | Azure CLI |
| GitHub Secrets | `VITE_API_KEY`, `VITE_MAP_URL=""`, `VITE_REALESTATE_URL=""` | gh CLI |

---

## ⚠️ 주의사항

- `API_KEY` 값을 `.env`, git, 채팅 등 어디에도 기록하지 말 것 — 터미널 변수로만 유지
- Phase 4(Container Apps 키 활성화)는 반드시 Phase 2 SWA 배포 완료 *후* 진행
- IP 제한 후 SWA를 통한 정상 동작을 반드시 재확인할 것
- 팀원이 로컬에서 Container Apps URL로 직접 테스트하려면 개발팀 IP를 Phase 5에서 추가해야 함

---

## 완료 후 상태 진단 요약

| 항목 | 완료 후 상태 |
|------|-------------|
| CORS | sohobi.net 명시적 허용, wildcard 제거 |
| SWA 역방향 프록시 | /api/*, /map/*, /realestate/* 모두 은폐 |
| API Key 인증 | /api/v1/* 전 엔드포인트 401 보호 |
| Private Endpoint | 미적용 (SWA 프록시+IP 제한으로 대체) |
| IP 화이트리스트 | Container Apps 인그레스: SWA IP만 허용 |
