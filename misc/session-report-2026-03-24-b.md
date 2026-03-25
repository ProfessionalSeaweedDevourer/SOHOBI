# 세션 리포트 — 2026-03-24 (2차)

## 배포 현황

- **Container Apps URL**: `https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io`
- **현재 브랜치**: PARK
- **배포된 코드**: PR #41까지 머지 (Chat Completions 전환)
- **열린 PR**: #42 (미검증, 머지 보류)

---

## 오늘 완료한 변경 (main 머지됨)

| PR | 파일 | 변경 내용 |
|----|------|-----------|
| #39 | `kernel_setup.py` | timeout 180s → 220s (Container Apps 240s 이내 에러 이벤트 전송 보장) |
| #39→revert | `signoff_agent.py` | `reasoning={"effort": "low"}` 추가 후 즉시 revert (gpt-5.4-pro 미지원) |
| #41 | `signoff_agent.py` | `responses.create()` → `chat.completions.create()` (Responses API 제거) |
| #41 | `kernel_setup.py` | signoff 클라이언트 AD 토큰 전용으로 고정, AI Foundry 엔드포인트 폴백 지원 |
| #41 | `frontend/.nvmrc` | Node 20 LTS 고정 (Oryx CDN Node 22.22.0 다운로드 실패 대응) |
| #41 | `.gitignore` | `logs/` 추가, 중복 공백 제거, `misc/.DS_Store` 추적 제거 |
| #41 | `CLAUDE.md` | **PR 머지 검증 규정 추가** — 동작 확인 전 머지 지시 금지 |

---

## signoff 미해결 — 오류 연대기 및 근본 원인 분석

### 오류 연대기

| 단계 | 시도 | 오류 | 원인 |
|------|------|------|------|
| 1 | gpt-5.4-pro + Responses API (원본) | 254초 hang | 추론 모델 실제 프롬프트 처리 시간 > Container Apps 240초 timeout |
| 2 | `reasoning={"effort": "low"}` 추가 | 400 unsupported_value | gpt-5.4-pro는 `low` 미지원 (`medium`/`high`/`xhigh`만 허용) |
| 3 | `AZURE_SIGNOFF_DEPLOYMENT=gpt-5-nano` | DeploymentNotFound | gpt-5-nano는 ejp-9638-resource에 미배포 |
| 4 | gpt-4.1-mini + AI Foundry 엔드포인트 | 401 wrong API key | `get_signoff_client()`에 `AZURE_OPENAI_API_KEY` 폴백 실수로 추가 → 일반 에이전트용 키가 signoff 엔드포인트로 전달됨 |
| 5 | API 키 폴백 제거 | 401 incorrect audience | `services.ai.azure.com`은 `cognitiveservices.azure.com` 토큰 거부 |
| 6 | `_SIGNOFF_TOKEN_PROVIDER` → `ai.azure.com/.default` | 400 API version not supported | **← 현재 위치** |

### 현재 400 오류의 근본 원인

`AsyncAzureOpenAI`가 `azure_endpoint` 기반으로 구성하는 URL:
```
{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version={version}
```

현재 설정으로 SDK가 실제 호출하는 URL:
```
https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638
  /openai/deployments/gpt-4.1-mini/chat/completions?api-version=2024-12-01-preview
```

AI Foundry의 실제 OpenAI 호환 엔드포인트 (api-version 없음):
```
https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638/openai/v1/chat/completions
```

**`AsyncAzureOpenAI`는 `/openai/deployments/.../` 경로 + `?api-version=` 을 강제로 붙이지만,
AI Foundry의 OpenAI 호환 엔드포인트는 `/openai/v1/` 경로를 사용하며 api-version을 받지 않음.**
어떤 api-version 값을 넣어도 경로 구조 자체가 다르므로 해결 불가.

---

## 현재 열린 PR #42 (미검증, 머지 보류)

| 파일 | 변경 내용 |
|------|-----------|
| `kernel_setup.py` | `_SIGNOFF_TOKEN_PROVIDER` (`ai.azure.com/.default`) 추가, `AZURE_SIGNOFF_API_VERSION` 환경변수 지원 (`2024-12-01-preview` 기본값) |

PR #42는 위 근본 원인으로 인해 현재 방식으로는 해결 불가. 내일 올바른 방향으로 업데이트 후 머지.

---

## 다음 세션 권장 조치

### 1단계: classic 엔드포인트 배포 확인 (Cloud Shell)

```bash
az cognitiveservices account deployment list \
  --name ejp-9638-resource \
  --resource-group rg-ejp-9638 \
  --query "[].{name:name, model:properties.model.name}" -o table
```

`gpt-4.1-mini`가 목록에 있으면 → **1-A 진행**.

### 1-A: classic Azure OpenAI 엔드포인트로 전환 (추천)

`AsyncAzureOpenAI` + classic 엔드포인트는 경로/api-version 문제 없음.
토큰 audience도 기존 `cognitiveservices.azure.com/.default` 재사용 가능.

**`kernel_setup.py` 변경:**
- `_SIGNOFF_TOKEN_PROVIDER` 제거 → `_TOKEN_PROVIDER` 재사용
- `api_version` → `AZURE_OPENAI_API_VERSION` 환경변수 재사용

**로컬 `.env` 변경:**
```
AZURE_SIGNOFF_ENDPOINT=https://ejp-9638-resource.openai.azure.com/
AZURE_SIGNOFF_DEPLOYMENT=gpt-4.1-mini
```

**로컬 검증:**
```bash
curl -s -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에서 카페를 열고 싶습니다"}'
```
`event: signoff_result` → `event: complete` 확인 후 PR #42 업데이트 → 머지.

### 1-B: gpt-4.1-mini가 classic 엔드포인트에 없는 경우

`openai.AsyncOpenAI` (비 Azure 클라이언트) + `base_url` 방식 사용:

```python
# base_url로 AI Foundry v1 엔드포인트 직접 지정 (api-version 불필요)
client = openai.AsyncOpenAI(
    base_url="https://ejp-9638-resource.services.ai.azure.com/api/projects/ejp-9638/openai/v1",
    api_key="placeholder",
    default_headers={"Authorization": f"Bearer {token}"},
    timeout=220.0,
)
```

AD 토큰을 `default_headers`에 직접 주입. `azure_ad_token_provider` 콜러블을 래핑하는 별도 유틸 필요.

---

## 기타 미완료 사항 (signoff 해결 후 진행)

| 항목 | 상태 |
|------|------|
| Cosmos DB 이름 확인 (`sohobi` / `sessions`) | ❌ 미실행 |
| `EXPORT_SECRET` Container Apps 시크릿 설정 | ❌ 미실행 |
| `original.pdf` NAM 팀 추가 | ❌ 미실행 |
| 프론트엔드 `VITE_API_URL` → Container Apps FQDN | ❌ sign-off 완료 후 |
| Railway 종료 | ❌ sign-off 완료 후 |
