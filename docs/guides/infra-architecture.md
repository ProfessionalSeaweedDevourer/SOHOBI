# SOHOBI 라이브 인프라 아키텍처

## 인프라 구성

```
[사용자 브라우저]
    │
    ▼
[Azure Static Web Apps (Free)] ── sohobi.net
│   • 프론트엔드: React + Vite 정적 빌드
│   • 리소스: <SWA_RESOURCE_NAME> / <RESOURCE_GROUP>
│   • ⚠️ Free 티어 — 역방향 프록시(route rewrite) 미지원
│   • 보안 헤더: HSTS, X-Frame-Options, X-Content-Type-Options
│
│  (브라우저가 Container Apps URL을 직접 호출 — SWA 프록시 경유 아님)
│
    ▼
[Azure Container Apps] ── <BACKEND_HOST> (`.env` 참조)
    • 백엔드: FastAPI + Uvicorn (Python 3.12)
    • 리소스: <CONTAINER_APP_NAME> / <RESOURCE_GROUP>
    • 환경변수는 Azure Portal 또는 az CLI로 관리 (로컬 .env와 별개)
    • Docker 이미지: ACR → GitHub Actions 자동 배포
```

## 환경변수: 로컬 `.env` vs Azure 프로덕션

**⚠️ 혼동 주의**: `backend/.env`는 **로컬 개발 전용**이다. 프로덕션 환경변수는 Azure Container Apps에 별도로 설정되며, 로컬 `.env`를 수정해도 프로덕션에 반영되지 않는다.

| 변수 | 로컬 `.env` | Azure Container Apps | 변경 방법 |
|------|-------------|---------------------|-----------|
| `API_SECRET_KEY` | 미설정 (인증 비활성) | 설정됨 (인증 활성) | `az containerapp update --set-env-vars` |
| `ALLOWED_IPS` | 비어있음 | 비어있음 (앱 레벨 IP 필터 비활성) | 동일 |
| `RATE_LIMIT_EXEMPT_IPS` | `127.0.0.1` 등 | 팀원 IP 등록 | 동일 |
| `CORS_EXTRA_ORIGINS` | `http://localhost:5173` | 빈 값 | 동일 |
| `BACKEND_HOST` | Container Apps URL | N/A (자기 자신) | — |

```bash
# 프로덕션 환경변수 변경
az containerapp update \
  --name <CONTAINER_APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --set-env-vars "변수명=값"

# 프로덕션 환경변수 현재 값 확인
az containerapp show \
  --name <CONTAINER_APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --query "properties.template.containers[0].env" -o table
```

## 보안 레이어 (외부 → 내부 순서)

| # | 레이어 | 위치 | 현재 상태 | 설정 방법 |
|---|--------|------|-----------|-----------|
| 1 | **인그레스 IP 제한** | Azure Container Apps 인프라 | ❌ 미적용 (Phase 5) | `az containerapp ingress access-restriction set` |
| 2 | **CORS** | 앱 코드 (`api_server.py`) | ✅ 적용 | 코드 수정 또는 `CORS_EXTRA_ORIGINS` |
| 3 | **Rate Limiting** | 앱 코드 (slowapi) | ✅ 적용 | `RATE_LIMIT_EXEMPT_IPS` |
| 4 | **API Key 인증** | 앱 코드 (`auth.py`) | ✅ 적용 | `API_SECRET_KEY` |
| 5 | **앱 레벨 IP 필터** | 앱 코드 (`_IPFilterMiddleware`) | ⬜ 비활성 | `ALLOWED_IPS` (SWA 프록시 환경에서 부정확 → 사용 자제) |

> **개발자 로컬 접근 허용**: 앱 레벨(#3, #5)은 `RATE_LIMIT_EXEMPT_IPS`로 해결. 인프라 레벨(#1)이 활성화되면 `az containerapp ingress access-restriction set`으로 별도 등록 필요.

### 인프라 레벨 IP 제한 (Phase 5) 적용 시 명령어

```bash
# 내 공인 IP 확인
curl -s ifconfig.me

# 또는 서버가 인식하는 IP 확인
curl -s $BACKEND_HOST/api/v1/my-ip

# 팀원 IP 등록
az containerapp ingress access-restriction set \
  --name <CONTAINER_APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --rule-name "allow-dev-PARK" \
  --ip-address <공인IP>/32 \
  --action Allow
```

## 배포 파이프라인

| 대상 | 트리거 | 워크플로우 |
|------|--------|-----------|
| 프론트엔드 (SWA) | `main` push (frontend 변경) | `.github/workflows/azure-static-web-apps-*.yml` |
| 백엔드 (Container Apps) | `main` push (backend 변경) | `.github/workflows/deploy-backend.yml` |

## Azure 리소스 요약

| 리소스 | 이름 | 리소스 그룹 |
|--------|------|-------------|
| Container Apps | `.env`의 `BACKEND_HOST` 참조 | `.env` 참조 |
| Static Web Apps | Azure Portal 참조 | 동일 |
| DNS zone | `sohobi.net` | 동일 |
| Subscription | Azure Portal 참조 | — |
