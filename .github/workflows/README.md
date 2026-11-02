# .github/workflows

GitHub Actions CI/CD 파이프라인.

---

## 워크플로우 목록

| 파일 | 이름 | 트리거 | 대상 |
|------|------|--------|------|
| `azure-static-web-apps.yml` | Azure Static Web Apps CI/CD | `frontend/**` 변경이 있는 `main` push, PR open/sync/reopen | 프론트엔드 (`frontend/`) → 새 구독 SWA `sohobi-prod-swa` |
| `azure-static-web-apps-cleanup.yml` | Azure Static Web Apps Cleanup | PR close, 매일 자정(UTC) cron, 수동 실행 | SWA PR preview 환경 정리 |
| `build-backend-new.yml` | Build Backend (new tenant) | 수동 실행 (`deploy=true` 면 리비전 갱신) | 백엔드 이미지 → ACR `sohobiprodacr` → Container App `sohobi-backend` (신규 테넌트 OIDC) |
| `smoke-test.yml` | Backend Smoke Test | `main` push, PR | 배포 후 헬스 체크 + API 키 인증 검증 |
| `azure-bicep-deploy.yml` | Bicep What-if / Deploy | PR(`infra/**` what-if), `main` push(deploy) | Azure 인프라 (Bicep IaC, 신규 테넌트 OIDC) |
| `pg-nightly-stop.yml` | PostgreSQL Nightly Stop | 야간 cron | PostgreSQL Flexible Server 정지 (비용 절감) |
| `workflow-keepalive.yml` | Workflow Keepalive | 매월 1일 cron, 수동 실행 | schedule 워크플로의 60일 무활동 자동 비활성화 방지 |

## 필요 GitHub Secrets

| Secret | 용도 |
|--------|------|
| `AZURE_CLIENT_ID_B`, `AZURE_TENANT_ID_B`, `AZURE_SUBSCRIPTION_ID_B` | 신규 테넌트 OIDC 로그인 (SWA 배포 토큰도 실행 중 이 로그인으로 받는다) |
| `PG_ADMIN_PASSWORD`, `JWT_SECRET`, `API_SECRET_KEY` | Bicep 필수 비밀값. `API_SECRET_KEY` 는 화면 빌드의 `VITE_API_KEY` 와 스모크 테스트에도 쓴다 |
| `KTO_GW_INFO_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `VWORLD_API_KEY`, `KAKAO_REST_KEY` | Bicep 선택 비밀값. VWorld, Kakao 는 비면 화면용 `VITE_VWORLD_API_KEY`, `VITE_KAKAO_API_KEY` 로 채운다 |
| `VITE_KAKAO_JS_KEY`, `VITE_KAKAO_API_KEY`, `VITE_VWORLD_API_KEY`, `VITE_DEV_PASSWORD_HASH` | 화면 빌드 |

백엔드 주소는 공개 값이라 secret 이 아니라 `azure-static-web-apps.yml`, `smoke-test.yml` 의 `env` 에 둔다.

## 특이사항

- 프론트엔드 워크플로우는 `frontend/**` 변경 PR에만 SWA preview 환경을 생성한다. docs/backend/infra PR은 Free tier preview slot을 사용하지 않는다
- SWA Free tier staging 환경 한도(3개)에 도달하면 preview deploy를 건너뛰고 PR 코멘트만 남긴다. 이 경우 CI는 실패시키지 않는다
- PR 닫힘 즉시 정리와 매일 stale cleanup은 `azure-static-web-apps-cleanup.yml`에서 전담한다
- SWA production 배포는 `concurrency` 설정으로 동시 배포를 큐잉하고, PR preview 배포는 같은 PR의 이전 실행을 취소한다
- 공개 리포는 60일 무활동 시 schedule 워크플로가 자동 비활성화된다(`disabled_inactivity`). schedule 워크플로를 추가하면 `workflow-keepalive.yml`의 `WORKFLOWS` 목록에도 추가한다
- 백엔드 배포(`build-backend-new.yml`)는 `concurrency` 설정으로 동시 배포를 방지한다 (`cancel-in-progress: false`). `backend/**` push 로 자동 배포되지 않는다. 옛 `deploy-backend.yml` 은 구 테넌트 정리(2026-10-22~23)로 죽어 2026-11-02 삭제했다
