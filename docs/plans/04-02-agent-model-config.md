# 에이전트별 독립 모델 설정 지원

## Context

현재 `kernel_setup.py`는 `"sign_off"` 서비스 하나만 등록하고, 모든 하위 에이전트(admin, finance, legal, location, chat)와 domain_router가 동일한 서비스를 공유한다. 이로 인해 에이전트별 다른 모델(예: admin→gpt-4o, router→gpt-4.1-mini)을 사용할 수 없다.

또한 실제 `.env`의 `AZURE_DEPLOYMENT_NAME=gpt-4.1-mini`로 인해, 의도한 gpt-4o 연결이 되지 않고 있었다.

**목표:** 에이전트별로 독립된 서비스 ID와 deployment 환경변수를 갖도록 구조를 변경. 기존 `.env`를 수정하지 않아도 동작하도록 fallback 패턴 적용.

---

## 수정 대상 파일

| 파일 | 변경 내용 |
|---|---|
| `integrated_PARK/kernel_setup.py` | 에이전트별 서비스 6개 등록, fallback 헬퍼 추가 |
| `integrated_PARK/agents/admin_agent.py` | `get_service("sign_off")` → `get_service("admin")` |
| `integrated_PARK/agents/finance_agent.py` | `get_service("sign_off")` → `get_service("finance")` (2곳) |
| `integrated_PARK/agents/legal_agent.py` | `get_service("sign_off")` → `get_service("legal")` |
| `integrated_PARK/agents/location_agent.py` | `get_service("sign_off")` → `get_service("location")` |
| `integrated_PARK/agents/chat_agent.py` | `get_service("sign_off")` → `get_service("chat")` |
| `integrated_PARK/domain_router.py` | `get_service("sign_off")` → `get_service("router")` |
| `integrated_PARK/.env.example` | 에이전트별 `AZURE_*_DEPLOYMENT` 변수 추가 |

---

## 구현 계획

### 1. `kernel_setup.py` 수정

```python
def _deployment(specific_var: str) -> str:
    """에이전트별 env var → 없으면 공통 AZURE_DEPLOYMENT_NAME으로 fallback"""
    return os.getenv(specific_var) or os.getenv("AZURE_DEPLOYMENT_NAME")

def get_kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

    agent_services = [
        ("admin",    "AZURE_ADMIN_DEPLOYMENT"),
        ("finance",  "AZURE_FINANCE_DEPLOYMENT"),
        ("legal",    "AZURE_LEGAL_DEPLOYMENT"),
        ("location", "AZURE_LOCATION_DEPLOYMENT"),
        ("chat",     "AZURE_CHAT_DEPLOYMENT"),
        ("router",   "AZURE_ROUTER_DEPLOYMENT"),
    ]
    for service_id, env_var in agent_services:
        kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=_deployment(env_var),
                endpoint=endpoint,
                api_key=api_key if api_key else None,
                ad_token_provider=None if api_key else _TOKEN_PROVIDER,
                api_version=api_version,
            )
        )
    return kernel
```

- `"sign_off"` 서비스 ID는 제거 (하위 에이전트 전용 ID로 분리)
- `get_signoff_client()`는 변경 없음 (signoff는 이미 별도 경로)
- 기존 `.env`에 `AZURE_*_DEPLOYMENT` 변수가 없어도 `AZURE_DEPLOYMENT_NAME`으로 fallback → **하위 호환 유지**

### 2. 각 에이전트 service ID 변경

| 에이전트 | 기존 | 변경 |
|---|---|---|
| admin_agent.py:89 | `"sign_off"` | `"admin"` |
| finance_agent.py:114, 145 | `"sign_off"` | `"finance"` |
| legal_agent.py:74 | `"sign_off"` | `"legal"` |
| location_agent.py:149 | `"sign_off"` | `"location"` |
| chat_agent.py:62 | `"sign_off"` | `"chat"` |
| domain_router.py:49 | `"sign_off"` | `"router"` |

### 3. `.env.example` 업데이트

기존 `AZURE_DEPLOYMENT_NAME=gpt-4o` 아래에 추가:

```
# 에이전트별 모델 오버라이드 (미설정 시 AZURE_DEPLOYMENT_NAME으로 fallback)
# AZURE_ADMIN_DEPLOYMENT=gpt-4o
# AZURE_FINANCE_DEPLOYMENT=gpt-4o
# AZURE_LEGAL_DEPLOYMENT=gpt-4o
# AZURE_LOCATION_DEPLOYMENT=gpt-4o
# AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
# AZURE_ROUTER_DEPLOYMENT=gpt-4.1-mini
```

---

## 검증 방법

1. 서버 재시작: `cd integrated_PARK && .venv/bin/python3 api_server.py`
2. 기본 동작 확인 (fallback 정상 작동):
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"question": "영업신고 절차 알려줘"}'
   ```
3. `.env`에 `AZURE_ADMIN_DEPLOYMENT=gpt-4o` 추가 후 재시작 → Azure Portal에서 gpt-4o 사용량 증가 확인
4. `.env`에 `AZURE_ROUTER_DEPLOYMENT=gpt-4.1-mini` 추가 → 모델 혼용 동작 확인
