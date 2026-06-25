# 세션 인수인계 — 좀비 리비전 자체 재활성 대응 (스케줄 청소 → 근본원인)

## 한 줄 요약

유지보수 모드 SOHOBI에서, 트래픽 0인 구 Container App 리비전 `sohobi-backend--0000008`이 **배포·수동조작과 무관하게 Azure 플랫폼이 자체적으로 재활성**시켜 유휴 컴퓨트 비용을 계속 만든다. 다음 세션에서 **(1) 스케줄 기반 자동 청소 → (2) 근본원인 제거** 순서로 마무리한다.

## 배경 (이번까지의 경위 — git/PR로 복구 가능, 참고용)

- SOHOBI는 **정식 종료 후 최소 비용 유지보수** 상태. 구독 `sohobi-prod`(eba83124-…) / RG `rg-sohobi-prod` / koreacentral.
- 6월 비용 급증(MTD ₩65.8K)의 ~91%가 좀비 리비전 `0000008`(6/11 테넌트 cutover 잔재)의 유휴 active vCPU. 실서비스 리비전은 `0000009`(traffic 100, scale-to-zero 정상).
- 이번 세션 완료분: PR **#368**(README 주간 자동갱신 워크플로 제거), **#369**(예산 알람 ₩60K→₩20K), **#370**(`azure-bicep-deploy.yml` deploy job에 "배포 후 트래픽0 구 리비전 자동 deactivate" self-heal 스텝 추가). MS 빌링 지원 케이스 **#2606230030003660** 접수(유휴분 ~₩55K 크레딧 요청, start 2026-06-11 / end 2026-06-23, 회신 대기).
- 예산 ₩20K는 실측 검증됨(5월 만월 ₩7,610=거의 ACR, baseline ~38%). 6/24 일비 ₩208로 평탄화 확인. 6월 MTD 329%는 좀비 누적 artifact(예상된 알람), 7월부터 ~₩7K 전망.
- (해결) 매일 09:47 `작업 요약 자동 생성` 커밋은 **사용자 개인 Anthropic 구독의 Claude 루틴**(입사 전 생성)이 주체 — SOHOBI 비용·인프라와 무관, 손대지 말 것.

## 이번 세션에서 새로 발견한 문제 (핵심)

- 6/25 점검 시 `0000008`이 다시 `active, replicas 1, traffic 0`. 즉시 재차단했으나:
  - 6/23 이후 **Bicep 배포 없음** → self-heal(배포 후에만 실행)이 돌 기회 없었음.
  - **활동 로그에 리비전 조작 이벤트 0건** → 사용자/CI가 아니라 **플랫폼 자체 재활성**.
- 즉 **Single revision 모드에서 `az containerapp revision deactivate`가 지속되지 않고**, 플랫폼이 배포와 무관하게 구 리비전을 되살린다. 현 self-heal은 "배포 직후"만 커버 → 배포 사이 공백 존재.
- **근본원인 가설:** 현 트래픽 리비전 `0000009`의 `healthState = None`(liveness probe 미설정) → 플랫폼이 마지막 Healthy였던 `0000008`을 fallback으로 유지하려 함.

## 다음 세션 작업 (순차)

### Task 1 — 스케줄 기반 자동 청소 (먼저, 확실·저위험)

- 목표: 플랫폼이 되살려도 몇 시간 내 자동 deactivate. 비용 상한 + ₩20K 알람 backstop.
- 방법: 이미 매일 여러 번(UTC 15:00/23:00/23:30/00:00) 도는 `.github/workflows/pg-nightly-stop.yml`에 청소 스텝 추가(Azure 로그인·RG env 재사용)하거나 전용 소형 daily 워크플로 신설.
- 로직은 이미 있음 — `.github/workflows/azure-bicep-deploy.yml`의 deploy job 스텝 **"Deactivate orphaned (0-traffic) revisions"** 를 그대로 복사: `active && trafficWeight==0` 중 latest 제외하고 deactivate. (env: `CONTAINER_APP_NAME=sohobi-backend`, `AZURE_RESOURCE_GROUP=rg-sohobi-prod`.)
- 검증: 머지 후 워크플로 1회 수동 실행 → 0000008 재활성 상태였다면 deactivate되는지, 며칠간 일비 평탄(₩200대) 유지되는지.

### Task 2 — 근본원인 제거 (Task 1 후)

- `0000009`를 단일 Healthy 리비전으로 확정해 플랫폼이 `0000008`을 fallback으로 안 부르게.
- 방법 (a): `infra/bicep/modules/container-app.bicep`의 `livenessProbePath`(현재 기본 `''`=probe 미설정)를 `/health`로 설정하고 `main.bicep`의 backendApp 모듈 호출에 전달 → 재배포로 `0000009`에 liveness probe 부여. (백엔드 `/health`는 200 반환 확인됨. probe는 컨테이너 targetPort 대상.)
- 방법 (b): 깨끗한 새 리비전 배포로 단일 latest 확정.
- 검증: 며칠간 `0000008`이 스스로 재활성 안 되는지. 확인되면 Task 1의 스케줄 청소는 backstop으로만 유지(제거 불필요).

---
<!-- CLAUDE_HANDOFF_START
branch: main (작업 브랜치 없음 — origin/main 기반 신규 단명 브랜치로 시작)
pr: none
prev: 2026-06-11-cutover-preload-handoff.md

[unresolved]
- HIGH ACA/sohobi-backend — 구 리비전 0000008이 플랫폼 자체로 재활성(배포·활동로그 무관, Single 모드 수동 deactivate 미지속). 유휴 컴퓨트 재과금. 해결: Task1 스케줄 청소 → Task2 0000009 liveness probe로 근본 제거
- MED MS 케이스 #2606230030003660 — 유휴분 ~₩55K 크레딧 요청 회신 대기(24~48 영업시간). 담당 v-sudatis@microsoft.com

[decisions]
- 유지보수 모드: 18-env/0-secret/managed-identity 최소구성은 의도된 정식 상태. env/secret 재팽창 금지(좀비 비용 재발)
- 예산 ₩20K는 실측 검증됨(5월 만월 ₩7,610 floor). 6월 MTD 329%는 좀비 artifact, 정상 아님 아님(=예상된 것)
- 일 09:47 dev-summary 커밋 = 사용자 개인 Anthropic 구독 Claude 루틴. SOHOBI 무관, 손대지 말 것

[next]
1. 스케줄 청소: pg-nightly-stop.yml(또는 신규 daily 워크플로)에 azure-bicep-deploy.yml deploy job의 "Deactivate orphaned (0-traffic) revisions" 로직 복사. env CONTAINER_APP_NAME=sohobi-backend
2. 근본원인: container-app.bicep livenessProbePath '' → '/health' 설정+main.bicep 전달, 재배포로 0000009 Healthy화 → 플랫폼이 0000008 fallback 중단 기대. 검증 며칠

[traps]
- 수동 `revision deactivate`는 Single 모드에서 안 붙음(플랫폼이 재활성) — 일회성 해결 신뢰 금지
- 전체 main.bicep 배포도 0000008 재활성(ARM reconcile) — self-heal 스텝이 배포 직후엔 정리하나 배포 사이는 공백
- gh 활성 계정이 rainbirdgeo면 PR 생성/머지 403 → `gh auth switch --user ProfessionalSeaweedDevourer`
- PR 머지: `gh pr merge <n> --admin --squash --delete-branch` (branch protection 우회, PARK admin)
- infra/bicep/** 또는 azure-bicep-deploy.yml 변경 머지 시 deploy job 트리거(~4분). PG state guard가 Stopped면 PG 기동
CLAUDE_HANDOFF_END -->
