# .github/workflows

GitHub Actions CI/CD 파이프라인.

---

## 워크플로우 목록

| 파일 | 이름 | 트리거 | 대상 |
|------|------|--------|------|
| `azure-static-web-apps-*.yml` | Azure Static Web Apps CI/CD | `main` push, PR open/sync/close, 매일 자정(UTC) cron | 프론트엔드 (`frontend/`) → Azure Static Web Apps |
| `deploy-backend.yml` | Deploy Backend to Azure Container Apps | `main` push (`integrated_PARK/**` 변경 시) | 백엔드 → Azure Container Apps (OIDC 인증) |
| `smoke-test.yml` | Backend Smoke Test | `main` push, PR | 배포 후 헬스 체크 + API 키 인증 검증 |
| `readme-update.yml` | Weekly README Auto-Update | 매주 일요일 15:00 UTC cron, 수동 | Claude Code CLI로 README 재생성 → PR 생성 |

## 필요 GitHub Secrets

| Secret | 용도 |
|--------|------|
| `AZURE_STATIC_WEB_APPS_API_TOKEN_*` | Static Web Apps 배포 토큰 |
| `AZURE_CLIENT_ID` | Azure OIDC 서비스 주체 |
| `AZURE_TENANT_ID` | Azure AD 테넌트 |
| `AZURE_SUBSCRIPTION_ID` | Azure 구독 |
| `VITE_API_URL` | 백엔드 API URL (스모크 테스트용) |
| `VITE_API_KEY` | API 키 (스모크 테스트용) |
| `ANTHROPIC_API_KEY` | Claude Code CLI 호출용 (README 자동 갱신) |

## 특이사항

- 프론트엔드 워크플로우는 PR별 스테이징 환경을 자동 생성하고, PR 닫힘 시 정리한다
- 백엔드 배포는 `concurrency` 설정으로 동시 배포를 방지한다 (`cancel-in-progress: false`)
