# SOHOBI 세션 작업 리포트 — 2026-03-23

## 개요

이 리포트는 2026-03-23 세션에서 수행한 모든 작업을 기록합니다.
브랜치: `PARK` → PR #26 (main 병합 대기)

---

## 1. SWA 배포 "Failed to Fetch" 수정

### 증상
Azure Static Web Apps에 배포된 프론트엔드에서 사용자 질의 및 로그 뷰어 양쪽에서 "오류: Failed to Fetch" 발생.

### 원인
`VITE_API_URL`은 Vite **빌드 시점** 치환 변수이나, Azure SWA App Settings는 런타임 Functions에만 전달되고 빌드 컨테이너에는 전달되지 않음. 결과적으로 `import.meta.env.VITE_API_URL`이 `undefined`로 번들링됨.

### 수정
| 파일 | 변경 내용 |
|------|-----------|
| `frontend/.env.production` | `VITE_API_URL=https://awake-victory-production-0a07.up.railway.app` 추가 |
| `.github/workflows/azure-static-web-apps-*.yml` | 빌드 스텝에 `env: VITE_API_URL:` 명시적 추가 |

### 커밋
`1fb11e7` — `fix: VITE_API_URL 빌드 시점 주입 및 SWA 워크플로우 추가`

### 상태
PR #26 오픈 — main 병합 시 SWA 자동 재빌드 예정

---

## 2. Azure OpenAI 권한 오류 수정 (401 PermissionDenied)

### 증상
```
Error code: 401 - {'error': {'code': 'PermissionDenied',
'message': 'The principal `bf2d4eda-...` lacks the required data action
`Microsoft.CognitiveServices/accounts/OpenAI/responses/write`'}}
```
도메인 분류 후 에이전트 작업 단계에서 signoff 호출 시 발생.

### 원인
Railway 서비스 주체(`bf2d4eda-bcef-4e4f-b311-aa41f5ad4c2a`)에 Responses API 전용 RBAC가 없었음. Chat Completions와 달리 Responses API는 별도의 데이터 액션(`responses/write`)을 요구함.

### 수정
Azure Portal / Cloud Shell에서 역할 할당:
```bash
az role assignment create \
  --assignee bf2d4eda-bcef-4e4f-b311-aa41f5ad4c2a \
  --role "Cognitive Services OpenAI Contributor" \
  --scope /subscriptions/5919b1b2-.../resourceGroups/rg-ejp-9638/providers/
          Microsoft.CognitiveServices/accounts/ejp-9638-resource
```

### 상태
완료 (코드 변경 없음)

---

## 3. Signoff C5 기준 완화

### 증상
"칵테일 바 오픈 절차" 질의에서 signoff가 C5 위반으로 거부:
> "해야 합니다", "밟아야 합니다" 등의 단정적 표현이 실제로 포함되어 있습니다.

### 원인 분석
C5(할루시네이션 징후 부재) 정의에 예시로 '반드시', '절대', '항상'만 명시되어 있었으나, signoff 모델이 의무형 어미 전반으로 과잉 확대 해석. '해야 합니다'는 법적 의무를 기술하는 행정 표준어로, 할루시네이션이 아닌 의무 서술임.

### 수정
4개 도메인 signoff 프롬프트 모두 C5 정의 수정:

| 파일 | 변경 |
|------|------|
| `prompts/signoff_admin/evaluate/skprompt.txt` | C5 반례 명시 추가 |
| `prompts/signoff_legal/evaluate/skprompt.txt` | C5 반례 명시 추가 |
| `prompts/signoff_finance/evaluate/skprompt.txt` | C5 반례 명시 추가 |
| `prompts/signoff_location/evaluate/skprompt.txt` | C5 반례 명시 추가 |

**변경 핵심**: "법적 의무를 기술하는 표준 행정 표현(예: '해야 합니다', '필요합니다', '밟아야 합니다')은 C5 위반이 아님" 명시.

### 커밋
`b4b084a` — `fix: C5 기준 완화 — 행정 의무 표현을 할루시네이션으로 오분류하지 않도록 반례 명시`

### 상태
완료 (Railway 재배포 없이 즉시 적용 — 프롬프트 파일 직접 로드)

---

## 4. Azure Container Apps 백엔드 마이그레이션 (진행 중)

### 목표
Railway → Azure Container Apps 이전으로 Azure 내부망 활용 및 관리형 아이덴티티 기반 인증 통합.

### 기대 효과
- 백엔드 → Azure OpenAI / Cosmos DB 구간 내부망 경유 (50~150ms 단축 예상)
- 관리형 아이덴티티로 비밀 자격증명 제거
- GitHub Actions CI/CD 파이프라인 통합

### 신규 파일
| 파일 | 내용 |
|------|------|
| `integrated_PARK/Dockerfile` | 멀티스테이지 빌드 (python:3.12-slim, wkhtmltopdf 포함) |
| `integrated_PARK/.dockerignore` | .venv, .env, logs 등 제외 |
| `.github/workflows/deploy-backend.yml` | ACR 빌드/푸시 → Container App 업데이트 |

### Azure 리소스 생성 현황

| 리소스 | 이름 | 상태 |
|--------|------|------|
| Azure Container Registry | `sohobi9638acr` | ✅ 생성 완료 |
| Container Apps 환경 | `sohobi-env` (koreacentral) | ✅ 생성 완료 |
| Container App | `sohobi-backend` | ✅ 생성 완료 |
| 시크릿 등록 | 10개 시크릿 | ✅ 완료 |
| 환경변수 연결 | secretref 참조 | ✅ 완료 |
| Azure OpenAI RBAC | Cognitive Services OpenAI Contributor | ✅ 완료 (principal: `7b98083a-...`) |
| Cosmos DB RBAC | Cosmos DB Built-in Data Contributor | ✅ 완료 |

### 잔여 작업

#### A. GitHub Actions OIDC 설정

Azure Portal → Azure Active Directory → 앱 등록 → 새 등록:
- 이름: `sohobi-github-actions`
- 지원 계정: 이 조직 디렉터리만

앱 등록 후 **페더레이션 자격증명** 추가:
- 시나리오: GitHub Actions
- 조직: `ProfessionalSeaweedDevourer`
- 리포지토리: `SOHOBI`
- 엔터티: Branch → `main`

앱 등록에 역할 할당 필요:
```bash
az role assignment create \
  --assignee <앱등록-클라이언트ID> \
  --role "AcrPush" \
  --scope /subscriptions/5919b1b2-.../resourceGroups/rg-ejp-9638/
          providers/Microsoft.ContainerRegistry/registries/sohobi9638acr

az role assignment create \
  --assignee <앱등록-클라이언트ID> \
  --role "Contributor" \
  --scope /subscriptions/5919b1b2-.../resourceGroups/rg-ejp-9638/
          providers/Microsoft.App/containerApps/sohobi-backend
```

#### B. GitHub 리포지토리 시크릿 등록

Settings → Secrets and variables → Actions:

| 시크릿 | 값 |
|--------|-----|
| `AZURE_CLIENT_ID` | 앱 등록 클라이언트 ID |
| `AZURE_TENANT_ID` | 테넌트 ID |
| `AZURE_SUBSCRIPTION_ID` | `5919b1b2-b639-42e1-8678-c28553b1661b` |
| `ACR_NAME` | `sohobi9638acr` |
| `CONTAINER_APP_NAME` | `sohobi-backend` |
| `RESOURCE_GROUP` | `rg-ejp-9638` |

#### C. Container App URL로 프론트엔드 업데이트

첫 배포 완료 후 Container App의 FQDN 확인:
```bash
az containerapp show \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --query properties.configuration.ingress.fqdn -o tsv
```

`frontend/.env.production`과 SWA 워크플로우의 `VITE_API_URL`을 새 URL로 업데이트.

#### D. PR #26 병합

main 병합 → SWA 자동 재빌드 → 프론트엔드 백엔드 연동 확인.

---

## 아키텍처 변화 요약

```
[변경 전]
프론트엔드(SWA) ──인터넷──→ 백엔드(Railway) ──인터넷──→ Azure OpenAI
                                             ──인터넷──→ Azure Cosmos DB

[변경 후]
프론트엔드(SWA) ──인터넷──→ 백엔드(Container Apps) ──내부망──→ Azure OpenAI
                                                   ──내부망──→ Azure Cosmos DB
```

---

*작성: Claude Code (claude-sonnet-4-6) — 2026-03-23*
