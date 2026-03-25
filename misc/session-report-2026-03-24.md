# 세션 리포트 — 2026-03-24

## 배포 현황

- **Container Apps URL**: `https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io`
- **Merged PR**: #38 (main ← PARK) — 2026-03-24, 배포 완료 확인 (CI/CD 2m3s)
- **현재 브랜치**: PARK (main과 동기 상태)

---

## 오늘 완료한 변경 (PR #38)

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/kernel_setup.py` | signoff 클라이언트 `timeout=180.0` 추가 (gpt-5.4-pro 추론 모델 지연 대응) |
| `integrated_PARK/signoff/signoff_agent.py` | `max_retries` 기본값 2→0 (1회만 실행, 응답 속도 개선) |
| `integrated_PARK/api_server.py` | 재무 변수 추출을 `asyncio.create_task()` 백그라운드 처리 |
| `integrated_PARK/nam/overlay_main.py` | NAM 폴더 Docker 빌드 컨텍스트 내로 이동 |
| `integrated_PARK/nam/malgun.ttf` | 동상 |
| `integrated_PARK/plugins/food_business_plugin.py` | `_NAM_DIR` 경로 `../NAM` → `./nam` 수정 |
| `integrated_PARK/railway.json` | `startCommand` 제거 (Dockerfile CMD `${PORT:-8000}` 폴백 위임) |

**⚠️ NAM 미완료**: `integrated_PARK/nam/original.pdf` 미포함 — NAM 팀 추가 필요

---

## 현재 상태

| 기능 | 상태 |
|------|------|
| 헬스체크 (`/health`) | ✅ 정상 |
| 도메인 분류 | ✅ 정상 |
| 서브 에이전트 (location/admin/finance/legal) | ✅ 정상 (~6–7초) |
| Sign-off | ❌ **미해결** — `signoff_start` 이후 이벤트 없음 |
| Cosmos DB 세션 | 미확인 |
| Blob Storage 로그 | 미확인 |

---

## Sign-off 미해결 문제 상세

### 증상
```
event: signoff_start
data: {"event": "signoff_start", "attempt": 1}
(이후 이벤트 없음 — --max-time 240 에서도 동일)
```

### 확인된 사실 (이슈 아님)
- `AZURE_SIGNOFF_ENDPOINT`: `https://ejp-9638-resource.openai.azure.com/` ✅
- `AZURE_SIGNOFF_DEPLOYMENT`: `gpt-5.4-pro` ✅ (실제 배포 존재 확인)
- RBAC: 관리 ID → ejp-9638-resource `Cognitive Services OpenAI Contributor` ✅ (2026-03-23 부여)
- Cloud Shell에서 Responses API 직접 호출 성공 ✅ (단순 입력 19초 소요)

### 가설 (우선순위 순)

**가설 1 — `json_object` 포맷이 추론 모델에서 미지원**
`signoff_agent.py:57`에서 `text={"format": {"type": "json_object"}}` 사용 중.
`gpt-5.4-pro`는 추론 모델(Reasoning model)이며, 일부 추론 모델은 `json_object` 포맷을 지원하지 않거나 다르게 동작함.
Cloud Shell 테스트는 이 파라미터 없이 호출 → 성공.
**→ 검증 명령 (Cloud Shell):**
```bash
TOKEN=$(az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv)
time curl -s -X POST "https://ejp-9638-resource.openai.azure.com/openai/responses?api-version=2025-04-01-preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5.4-pro", "input": [{"role": "user", "content": "respond with json {\"ok\": true}"}], "text": {"format": {"type": "json_object"}}}'
```
실패(400 등) 또는 매우 느린 경우 → 포맷 제거 또는 `json_schema`로 변경.

**가설 2 — 추론 모델의 signoff 평가 소요 시간 > 240초**
단순 입력 19초 → 실제 signoff 프롬프트(10개 평가 항목 + 수백 토큰 draft) 는 200–600초 가능성.
`timeout=180.0` 이 먼저 발동되어야 하나 `event: error` 도 수신되지 않음.
**→ 검증: `time curl` 로 정확한 소요 시간 측정**
```bash
time curl -s -N -X POST \
  https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에서 카페를 열고 싶습니다"}' \
  --max-time 240
```
- `real ≈ 180s` → timeout 발동, 에러 이벤트 미수신 → 에러 핸들링 버그
- `real ≈ 240s` → 모델이 240초 이상 소요 → 타임아웃 상향 또는 모델 변경 필요

**가설 3 — `timeout=180.0` 이 배포 코드에 실제로 반영되지 않음**
배포 로그 성공했으나, 컨테이너 재시작 후에도 이전 이미지 사용 가능성 (낮음).

---

## 다음 세션 권장 조치 (우선순위)

### 1단계: 정확한 소요 시간 측정
```bash
time curl -s -N -X POST \
  https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 마포구에서 카페를 열고 싶습니다"}' \
  --max-time 300
```

### 2단계: Cloud Shell에서 json_object 포맷 테스트
위 가설 1 명령 실행

### 3단계-A (json_object 문제인 경우): 포맷 제거
`signoff_agent.py:54–58` 수정:
```python
# 변경 전
response = await client.responses.create(
    model=deployment,
    input=messages,
    text={"format": {"type": "json_object"}},
)

# 변경 후 (포맷 제약 제거)
response = await client.responses.create(
    model=deployment,
    input=messages,
)
```
프롬프트에 "반드시 JSON만 출력" 지시가 있으므로 포맷 없이도 JSON 반환 가능.

### 3단계-B (모델 속도 문제인 경우): 추론 노력 낮추기
```python
response = await client.responses.create(
    model=deployment,
    input=messages,
    text={"format": {"type": "json_object"}},
    reasoning={"effort": "low"},  # medium → low
)
```

### 3단계-C (근본적 해결): signoff 모델을 빠른 모델로 교체
`gpt-5.4-pro`(추론) → 일반 GPT-4o 계열로 전환.
`AZURE_SIGNOFF_DEPLOYMENT` 비밀값 변경, 또는 별도 배포 사용.

---

## 기타 미완료 사항

| 항목 | 상태 |
|------|------|
| Cosmos DB 이름 확인 (sohobi / sessions) | ❌ 미실행 |
| `EXPORT_SECRET` 설정 | ❌ 미실행 |
| `original.pdf` NAM 팀 추가 | ❌ 미실행 |
| 프론트엔드 `VITE_API_URL` Container Apps FQDN으로 변경 | ❌ sign-off 작동 후 진행 |
| Railway 종료 | ❌ sign-off 작동 후 진행 |

### Cosmos DB 확인 명령 (Cloud Shell)
```bash
az cosmosdb sql database list \
  --account-name sohobi-ejp-9638 \
  --resource-group rg-ejp-9638 \
  --query "[].id" -o tsv

az cosmosdb sql container list \
  --account-name sohobi-ejp-9638 \
  --resource-group rg-ejp-9638 \
  --database-name sohobi \
  --query "[].id" -o tsv
```

### EXPORT_SECRET 설정 (Cloud Shell)
```bash
az containerapp secret set \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --secrets export-secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```
