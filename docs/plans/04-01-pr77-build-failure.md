# PR #77 빌드 실패 해결 계획

## Context

Azure Static Web Apps (SWA) free tier는 최대 3개의 staging environment(PR preview)만 허용한다. PR #77 (NAM 브랜치)이 새 staging environment를 생성하려 했으나 이미 한도에 도달해 빌드 실패.

오류 메시지:
> This Static Web App already has the maximum number of staging environments. Please remove one and try again.

현재 열린 PR은 #77 하나뿐이므로, 이전에 닫힌 PR들의 cleanup 워크플로우가 실패했거나 staging environment를 제대로 삭제하지 못한 것으로 보인다.

## 원인

Azure SWA 토큰 만료(`az login` 필요). 직접 staging environment 목록을 확인할 수 없어 수동 삭제 필요.

## 해결 절차

### 1단계: Azure CLI 재인증
```bash
az login --tenant 62ae463a-9f12-4edf-8544-4f6ca3834524
```

### 2단계: SWA 리소스 그룹 및 staging environment 확인
```bash
# SWA 리소스 그룹 확인
az staticwebapp list --query "[?name=='<SWA_RESOURCE_NAME>'].{name:name, rg:resourceGroup}" -o table

# staging environment 목록 조회
az staticwebapp environment list \
  --name <SWA_RESOURCE_NAME> \
  --resource-group <리소스그룹명> \
  -o table
```

### 3단계: 오래된 staging environment 삭제
PR #77 (NAM 브랜치) 외 나머지 환경 삭제:
```bash
az staticwebapp environment delete \
  --name <SWA_RESOURCE_NAME> \
  --resource-group <리소스그룹명> \
  --environment-name <환경명> \
  --yes
```
환경명은 보통 PR 번호 (`pr-73`, `pr-74` 등) 형식.

### 4단계: PR #77 워크플로우 재실행
```bash
gh workflow run azure-static-web-apps-<SWA_RESOURCE_NAME>.yml \
  --ref NAM
```
또는 GitHub UI에서 실패한 run을 "Re-run" 클릭.

## 검증

워크플로우 완료 후:
```bash
gh run list --workflow=azure-static-web-apps-<SWA_RESOURCE_NAME>.yml --limit 3
```
conclusion이 `success`이면 완료.

## 관련 파일

- [.github/workflows/azure-static-web-apps-<SWA_RESOURCE_NAME>.yml](.github/workflows/azure-static-web-apps-<SWA_RESOURCE_NAME>.yml) — SWA 배포 워크플로우
