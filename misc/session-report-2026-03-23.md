# SOHOBI 세션 작업 리포트 — 2026-03-23

## 개요

브랜치: `PARK`
PR 현황: #26 ✅ #27 ✅ #29 ✅ #30 ✅ 병합 완료 / #31 🔄 병합 대기

---

## 1. SWA 배포 "Failed to Fetch" 수정 ✅

### 증상
Azure Static Web Apps에 배포된 프론트엔드에서 사용자 질의 및 로그 뷰어 양쪽에서 "오류: Failed to Fetch" 발생.

### 원인
`VITE_API_URL`은 Vite **빌드 시점** 치환 변수이나, Azure SWA App Settings는 런타임 Functions에만 전달되고 빌드 컨테이너에는 전달되지 않음. 결과적으로 `import.meta.env.VITE_API_URL`이 `undefined`로 번들링됨.

### 수정
| 파일 | 변경 내용 |
|------|-----------|
| `frontend/.env.production` | `VITE_API_URL=https://awake-victory-production-0a07.up.railway.app` 추가 |
| `.github/workflows/azure-static-web-apps-*.yml` | 빌드 스텝에 `env: VITE_API_URL:` 명시적 추가 |

**PR #26** 병합 완료

---

## 2. Azure OpenAI Responses API 권한 오류 수정 ✅

### 증상
```
Error code: 401 - PermissionDenied
lacks the required data action:
Microsoft.CognitiveServices/accounts/OpenAI/responses/write
```

### 원인
Railway 서비스 주체(`bf2d4eda-...`)에 Responses API 전용 RBAC 누락.
Chat Completions와 달리 Responses API는 별도의 데이터 액션을 요구함.

### 수정 (Azure Portal / Cloud Shell)

```bash
az role assignment create \
  --assignee bf2d4eda-bcef-4e4f-b311-aa41f5ad4c2a \
  --role "Cognitive Services OpenAI Contributor" \
  --scope .../Microsoft.CognitiveServices/accounts/ejp-9638-resource
```
코드 변경 없음.

---

## 3. Signoff C5 기준 완화 ✅

### 증상
"칵테일 바 오픈 절차" 질의에서 signoff가 C5 위반으로 거부:
`'해야 합니다', '밟아야 합니다' 등의 단정적 표현이 실제로 포함되어 있습니다.`

### 원인
signoff 모델이 C5 예시('반드시', '절대', '항상')를 확대 해석해 행정 의무 서술 표현 전반을 할루시네이션으로 판정.

### 수정
4개 도메인 signoff 프롬프트 C5 정의에 반례 명시:

> "법적 의무를 기술하는 표준 행정 표현(예: '해야 합니다', '필요합니다', '밟아야 합니다')은 C5 위반이 아니다 — 이는 할루시네이션이 아니라 의무 서술이다."

파일: `prompts/signoff_{admin,legal,finance,location}/evaluate/skprompt.txt`

**PR #27** 병합 완료 (Railway 재배포 없이 즉시 적용)

---

## 4. Azure Container Apps 백엔드 마이그레이션 🔄

### 목표
Railway → Azure Container Apps 이전으로 Azure 내부망 활용, 관리형 아이덴티티 기반 인증 통합.

### 기대 효과
- 백엔드 ↔ Azure OpenAI / Cosmos DB 구간 내부망 경유 (50~150ms 단축 예상)
- 관리형 아이덴티티로 비밀 자격증명 제거
- GitHub Actions CI/CD 파이프라인 자동화

### 아키텍처 변화

```
[변경 전]
프론트엔드(SWA) ──인터넷──→ 백엔드(Railway, asia-southeast1)
                                ──인터넷──→ Azure OpenAI (East US 2)
                                ──인터넷──→ Azure Cosmos DB

[변경 후]
프론트엔드(SWA) ──인터넷──→ 백엔드(Container Apps, koreacentral)
                                ──내부망──→ Azure OpenAI (GlobalStandard)
                                ──내부망──→ Azure Cosmos DB
```

### 신규 파일
| 파일 | 내용 |
|------|------|
| `integrated_PARK/Dockerfile` | 멀티스테이지 빌드 (`python:3.12-slim-bookworm`, wkhtmltopdf 포함) |
| `integrated_PARK/.dockerignore` | .venv, .env, logs 등 제외 |
| `.github/workflows/deploy-backend.yml` | ACR 빌드/푸시 → Container App 자동 배포 (OIDC) |

### Dockerfile 수정 이력

- `python:3.12-slim` → `python:3.12-slim-bookworm` 고정
  원인: Debian Trixie(13)에서 `wkhtmltopdf` 패키지 제거됨

### Azure 리소스 현황

| 리소스 | 이름 | 위치 | 상태 |
|--------|------|------|------|
| Azure Container Registry | `sohobi9638acr` | koreacentral | ✅ |
| Container Apps 환경 | `sohobi-env` | koreacentral | ✅ |
| Container App | `sohobi-backend` | koreacentral | ✅ |
| 시크릿 (10개) | — | — | ✅ |
| 환경변수 연결 | secretref 참조 | — | ✅ |
| Azure OpenAI RBAC | Cognitive Services OpenAI Contributor | — | ✅ |
| Cosmos DB RBAC | Cosmos DB Built-in Data Contributor | — | ✅ |
| ACR Pull RBAC (Container App) | AcrPull | — | ✅ |

### GitHub Actions OIDC 설정

- 서비스 주체: `bf2d4eda-...` (Railway와 공용)
- 페더레이션 자격증명: `repo:ProfessionalSeaweedDevourer/SOHOBI:ref:refs/heads/main`
- GitHub 시크릿 6개 등록 완료

### GitHub Actions 배포 현황

- PR #29 병합 → 워크플로우 실패 (AcrPull 권한 누락)
- PR #30 병합 (bookworm 수정) → 워크플로우 실패 (동일 원인)
- AcrPull 권한 부여 후 재실행 → **진행 중**

### 잔여 작업 (다음 세션)

#### A. Container App 배포 성공 확인

```bash
# 헬스 체크
curl https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/health
```

#### B. 프론트엔드 백엔드 URL 전환

`frontend/.env.production` 및 SWA 워크플로우의 `VITE_API_URL`을 Railway URL에서 Container Apps FQDN으로 교체:

```
https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io
```

#### C. Railway 서비스 종료

프론트엔드 전환 확인 후 Railway 프로젝트 비활성화.

---

## 5. Blob Storage 로그 영구 저장 🔄

### 배경
Container Apps 컨테이너는 에페머럴(임시) — 재시작/스케일 시 `/app/logs/*.jsonl` 소멸.

### 구현

- `BLOB_LOGS_ACCOUNT` 환경변수 설정 시 Azure Blob Storage에 기록
- 미설정 시 로컬 파일 폴백 (로컬 개발 환경 무설정 동작 유지)
- append blob 사용 → JSONL 형식 그대로 유지
- `/api/v1/logs` 엔드포인트 및 프론트엔드 로그 뷰어 코드 변경 없음

```
Azure Storage Account (sohobi9638logs)
  └─ 컨테이너: sohobi-logs
       ├─ queries.jsonl
       ├─ rejections.jsonl
       └─ errors.jsonl
```

**PR #31** 병합 대기

### 잔여 Azure 설정

아래 Cloud Shell 명령 참조.

---

## 내일 시작 시 Cloud Shell 실행 명령

### 1. Blob Storage 설정 (PR #31 병합 후)

```bash
RG=rg-ejp-9638
SUBSCRIPTION=5919b1b2-b639-42e1-8678-c28553b1661b
SA_NAME=sohobi9638logs

# Storage Account 생성
az storage account create \
  --name $SA_NAME \
  --resource-group $RG \
  --location koreacentral \
  --sku Standard_LRS \
  --allow-blob-public-access false

# 로그 컨테이너 생성
az storage container create \
  --name sohobi-logs \
  --account-name $SA_NAME \
  --auth-mode login

# Container App 관리형 아이덴티티에 쓰기 권한
PRINCIPAL=$(az containerapp show \
  --name sohobi-backend --resource-group $RG \
  --query identity.principalId -o tsv)

az role assignment create \
  --assignee $PRINCIPAL \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$SUBSCRIPTION/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$SA_NAME

# Container App에 환경변수 추가
az containerapp update \
  --name sohobi-backend \
  --resource-group $RG \
  --set-env-vars BLOB_LOGS_ACCOUNT=$SA_NAME
```

### 2. 배포 확인

```bash
# 헬스 체크
curl https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/health

# 실제 질의 테스트
curl -s -X POST \
  https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에서 카페를 열고 싶습니다"}'
```

### 3. 프론트엔드 URL 전환 (배포 확인 후)

`frontend/.env.production` 수정:

```
VITE_API_URL=https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io
```

SWA 워크플로우(`.github/workflows/azure-static-web-apps-*.yml`)의 `env.VITE_API_URL`도 동일하게 수정 후 커밋 → PR → 병합.

### 4. Railway 종료

프론트엔드 전환 및 동작 확인 후 Railway 대시보드에서 프로젝트 비활성화 또는 삭제.

---

## 전체 PR 이력

| PR | 제목 | 상태 |
| --- | --- | --- |
| #26 | fix: VITE_API_URL 빌드 주입 및 SWA 배포 워크플로우 | ✅ 병합 |
| #27 | fix: C5 기준 완화 | ✅ 병합 |
| #29 | feat: Azure Container Apps 배포 파이프라인 및 Signoff C5 기준 완화 | ✅ 병합 |
| #30 | fix: Dockerfile 베이스 이미지 bookworm 고정 | ✅ 병합 |
| #31 | feat: Blob Storage 로그 영구 저장 | 🔄 병합 대기 |

---

*작성: Claude Code (claude-sonnet-4-6) — 2026-03-23*
