# .github/workflows

GitHub Actions CI/CD 파이프라인.

---

## 워크플로우 목록

| 파일 | 이름 | 트리거 | 대상 |
|------|------|--------|------|
| `azure-static-web-apps-delightful-rock-0de6c000f.yml` | Azure Static Web Apps CI/CD | `frontend/**` 변경이 있는 `main` push, PR open/sync/reopen | 프론트엔드 (`frontend/`) → Azure Static Web Apps |
| `azure-static-web-apps-cleanup.yml` | Azure Static Web Apps Cleanup | PR close, 매일 자정(UTC) cron, 수동 실행 | SWA PR preview 환경 정리 |
| `deploy-backend.yml` | Deploy Backend to Azure Container Apps | `main` push (`backend/**` 변경 시) | 백엔드 → Azure Container Apps (OIDC 인증) |
| `smoke-test.yml` | Backend Smoke Test | `main` push, PR | 배포 후 헬스 체크 + API 키 인증 검증 |
| `azure-bicep-deploy.yml` | Bicep What-if / Deploy | PR(`infra/**` what-if), `main` push(deploy) | Azure 인프라 (Bicep IaC, 신규 테넌트 OIDC) |
| `pg-nightly-stop.yml` | PostgreSQL Nightly Stop | 야간 cron | PostgreSQL Flexible Server 정지 (비용 절감) |

## 필요 GitHub Secrets

| Secret | 용도 |
|--------|------|
| `AZURE_STATIC_WEB_APPS_API_TOKEN_*` | Static Web Apps 배포 토큰 |
| `AZURE_CLIENT_ID` | Azure OIDC 서비스 주체 |
| `AZURE_TENANT_ID` | Azure AD 테넌트 |
| `AZURE_SUBSCRIPTION_ID` | Azure 구독 |
| `VITE_API_URL` | 백엔드 API URL (스모크 테스트용) |
| `VITE_API_KEY` | API 키 (스모크 테스트용) |

## 특이사항

- 프론트엔드 워크플로우는 `frontend/**` 변경 PR에만 SWA preview 환경을 생성한다. docs/backend/infra PR은 Free tier preview slot을 사용하지 않는다
- SWA Free tier staging 환경 한도(3개)에 도달하면 preview deploy를 건너뛰고 PR 코멘트만 남긴다. 이 경우 CI는 실패시키지 않는다
- PR 닫힘 즉시 정리와 매일 stale cleanup은 `azure-static-web-apps-cleanup.yml`에서 전담한다
- SWA production 배포는 `concurrency` 설정으로 동시 배포를 큐잉하고, PR preview 배포는 같은 PR의 이전 실행을 취소한다
- 백엔드 배포는 `concurrency` 설정으로 동시 배포를 방지한다 (`cancel-in-progress: false`)
