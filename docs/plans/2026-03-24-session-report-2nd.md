# 세션 리포트 작성 — 2026-03-24 (2차)

## Context
오늘 signoff 문제 해결을 시도했으나 API 버전 이슈로 미완. 이번 세션의 전체 변경 이력,
현재 남은 문제의 근본 원인 분석, 내일 조치 계획을 `misc/session-report-2026-03-24-b.md`로 작성.

---

## 오늘 세션 전체 요약 (문서에 기록할 내용)

### 완료 및 main 머지된 PR
| PR | 내용 | 상태 |
|----|------|------|
| #39 | timeout 220s + effort=low | MERGED (effort=low는 이후 revert) |
| #40 | effort=low revert + Chat Completions 전환 + SWA Node 20 고정 | MERGED |
| #41 | gitignore 정리, .DS_Store 제거 | MERGED |

### 현재 열린 PR
| PR | 내용 | 상태 |
|----|------|------|
| #42 | AI Foundry audience 토큰 + API 버전 변경 + CLAUDE.md 규정 | **OPEN** (미검증) |

---

## signoff 오류 연대기 (근본 원인 분석 포함)

| 단계 | 시도 | 오류 | 원인 |
|------|------|------|------|
| 1 | gpt-5.4-pro Responses API (원본) | 254초 hang | 추론 모델 속도 > Container Apps 240초 timeout |
| 2 | effort="low" 추가 | 400 unsupported_value | gpt-5.4-pro는 low 미지원 (medium/high/xhigh만) |
| 3 | gpt-5-nano 전환 시도 | DeploymentNotFound | gpt-5-nano는 ejp-9638-resource에 미배포 |
| 4 | gpt-4.1-mini + Chat Completions API (AI Foundry 엔드포인트) | 401 wrong API key | get_signoff_client()에 AZURE_OPENAI_API_KEY 폴백 로직 실수로 추가 |
| 5 | API 키 폴백 제거 | 401 incorrect audience | services.ai.azure.com은 cognitiveservices.azure.com 토큰 거부 |
| 6 | _SIGNOFF_TOKEN_PROVIDER → ai.azure.com/.default | 400 API version not supported | **← 현재 위치** |

### 현재 400 오류의 근본 원인

`AsyncAzureOpenAI`가 `azure_endpoint`를 기반으로 구성하는 URL:
```
{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version={version}
```

현재 설정값:
```
https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638
  /openai/deployments/gpt-4.1-mini/chat/completions?api-version=2024-12-01-preview
```

AI Foundry의 실제 OpenAI 호환 엔드포인트 (api-version 없음):
```
https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638/openai/v1/chat/completions
```

`AsyncAzureOpenAI`는 `/openai/deployments/.../` 경로 + api-version을 강제로 붙이지만,
AI Foundry는 `/openai/v1/` 경로를 사용하며 api-version을 받지 않음 → 경로 구조 불일치.

---

## 내일 조치 계획 (우선순위)

### 1단계: classic 엔드포인트로 전환 시도 (추천)

gpt-4.1-mini가 `ejp-9638-resource`에 배포된 경우, classic Azure OpenAI 엔드포인트로
접근 가능 — SDK 경로 불일치 문제 없음, 토큰 audience도 기존 것 그대로 사용 가능.

**Cloud Shell에서 먼저 확인:**
```bash
az cognitiveservices account deployment list \
  --name ejp-9638-resource \
  --resource-group rg-ejp-9638 \
  --query "[].{name:name, model:properties.model.name}" -o table
```
gpt-4.1-mini가 목록에 있으면 → 1단계 진행.

**코드 변경 (kernel_setup.py):**
- `_SIGNOFF_TOKEN_PROVIDER` → `cognitiveservices.azure.com/.default` 복원 (또는 제거하고 `_TOKEN_PROVIDER` 재사용)
- `api_version` → `AZURE_OPENAI_API_VERSION` 환경변수 공유 (2024-05-01-preview)

**환경변수 변경 (로컬 .env):**
```
AZURE_SIGNOFF_ENDPOINT=https://ejp-9638-resource.openai.azure.com/
AZURE_SIGNOFF_DEPLOYMENT=gpt-4.1-mini
```

**검증:**
```bash
curl -s -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에서 카페를 열고 싶습니다"}'
```
`event: signoff_result` → `event: complete` 확인 후 PR #42 업데이트 → 머지.

---

### 2단계: 1단계 실패 시 — openai.AsyncOpenAI + base_url

gpt-4.1-mini가 classic 엔드포인트에 없는 경우:
- `openai.AsyncOpenAI(base_url=".../openai/v1", api_key="unused")`
- `default_headers={"Authorization": "Bearer {token}"}` 방식으로 AD 토큰 직접 주입
- api-version 불필요 (OpenAI 호환 엔드포인트)

---

## 기타 미완료 사항 (signoff 해결 후)

| 항목 | 상태 |
|------|------|
| Cosmos DB 이름 확인 | ❌ 미실행 |
| EXPORT_SECRET 설정 | ❌ 미실행 |
| original.pdf (NAM 팀) | ❌ 미실행 |
| 프론트엔드 VITE_API_URL Container Apps FQDN으로 변경 | ❌ sign-off 완료 후 |
| Railway 종료 | ❌ sign-off 완료 후 |

---

## 현재 배포 현황

| 항목 | 값 |
|------|-----|
| Container Apps URL | https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io |
| 배포된 코드 | PR #41까지 (Chat Completions 전환) |
| AZURE_SIGNOFF_ENDPOINT | https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638 |
| AZURE_SIGNOFF_DEPLOYMENT | gpt-4.1-mini |
| signoff 동작 여부 | ❌ API version 오류 (400) |
| 서브 에이전트 | ✅ 정상 (~6–7초) |
