# SOHOBI 백엔드 보안 강화 계획

## Context

프론트엔드(`sohobi.net`, Azure SWA)에서 백엔드(Azure Container Apps)를 직접 호출하는 구조상,
백엔드 URL이 브라우저 개발자도구에 노출된다. 현재 백엔드는 사실상 인터넷에 완전 개방된 상태이며,
다음 5가지 기준에 대한 현황 분석 및 보완 방안을 기획한다.

**개발 단계 제약:** 현재 로컬 환경에서 curl·스트레스 테스트를 진행 중이므로,
모든 보안 기능은 **환경변수가 설정된 경우에만 활성화**되는 구조로 구현한다.
로컬에서는 환경변수를 설정하지 않으면 기존과 동일하게 동작하고,
프로덕션(Azure Container Apps)에서만 환경변수를 활성화하는 방식으로 분리한다.

> **참고:** CORS는 브라우저 전용 메커니즘이므로 curl 테스트에는 전혀 영향을 주지 않는다.
> API Key 인증과 IP 필터는 환경변수 미설정 시 비활성화되므로 로컬 curl 테스트가 그대로 통과한다.

---

## 현재 상태 진단 요약

| 항목 | 현재 준수 수준 | 위험도 |
|------|----------------|--------|
| CORS | `allow_origins=["*"]` — 전체 허용 | HIGH |
| API Gateway / 역방향 프록시 | 없음 — 백엔드 URL 직접 노출 | HIGH |
| JWT/인증 | 모든 API 엔드포인트 무인증 개방 | HIGH |
| Private Endpoint | 없음 — External ingress | MEDIUM |
| IP 화이트리스트 | 없음 | MEDIUM |

---

## 항목별 구현 계획

### 1. CORS 제한 (`integrated_PARK/api_server.py:48-54`)

**현재:** `allow_origins=["*"]` + `allow_credentials=True` — 브라우저가 이 조합을 실제로 거부하므로
프론트엔드도 credentials 없이 동작 중이거나 오작동 중일 가능성 높음.
curl 같은 non-browser 클라이언트는 CORS 헤더를 무시하므로 백엔드는 완전히 개방된 상태.

**수정 내용:**
```python
# api_server.py:48-54 교체
ALLOWED_ORIGINS = [
    "https://sohobi.net",
    "https://www.sohobi.net",
    "https://delightful-rock-0de6c000f.6.azurestaticapps.net",
    # 로컬 개발 — 환경변수로 제어
]
_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra:
    ALLOWED_ORIGINS.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    max_age=600,
)
```

**Azure 환경변수 추가:**
- Container Apps: `CORS_EXTRA_ORIGINS=""` (운영 시 빈 문자열)

---

### 2. Azure API Gateway / 역방향 프록시

**권장: Azure Static Web Apps 내장 프록시 (무료)**

SWA의 `routes` 규칙으로 `/api/*`를 Container Apps URL로 프록시.
프론트엔드 JS에서 백엔드 URL이 사라지고, 브라우저에는 `sohobi.net/api/...`만 노출된다.

**`frontend/staticwebapp.config.json` 수정:**
```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/assets/*", "/*.css", "/*.js", "/api/*"]
  },
  "routes": [
    {
      "route": "/api/*",
      "rewrite": "https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/*"
    }
  ],
  "globalHeaders": {
    "Cache-Control": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
  }
}
```

**`frontend/src/api.js` 수정:**
- `VITE_API_URL` 환경변수 제거
- `BASE_URL = ""` (상대경로)로 변경 → 모든 `fetch` 호출이 `/api/...`로

**비용:** 무료. SWA 재배포 필요.

---

### 3. JWT/API Key 인증 (`integrated_PARK/auth.py` 신규 + `api_server.py` 수정)

**현재:** 모든 API 엔드포인트 완전 무인증.
`/api/v1/logs`는 모든 쿼리 로그를 인증 없이 노출 — 즉시 차단 필요.

**신규 파일: `integrated_PARK/auth.py`**
```python
import os, hmac
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_API_KEY = os.getenv("API_SECRET_KEY", "")
security = HTTPBearer(auto_error=False)

def verify_api_key(
    authorization: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    if not _API_KEY:
        return  # 개발 모드: 환경변수 미설정 시 통과
    token = (authorization.credentials if authorization else None) or x_api_key
    if not token or not hmac.compare_digest(token, _API_KEY):
        raise HTTPException(status_code=401, detail="인증 필요")
```

**`api_server.py` 수정 — 각 엔드포인트에 의존성 추가:**
```python
from auth import verify_api_key

@app.post("/api/v1/query", dependencies=[Depends(verify_api_key)])
@app.post("/api/v1/stream", dependencies=[Depends(verify_api_key)])
@app.post("/api/v1/signoff", dependencies=[Depends(verify_api_key)])
@app.post("/api/v1/doc/chat", dependencies=[Depends(verify_api_key)])
@app.get("/api/v1/logs", dependencies=[Depends(verify_api_key)])  # ← 특히 중요
```

**`frontend/src/api.js` 수정:**
```javascript
const API_KEY = import.meta.env.VITE_API_KEY || "";
const authHeaders = {
  "Content-Type": "application/json",
  ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
};
// 모든 fetch 호출에 authHeaders 적용
```

**환경변수:**
- Container Apps: `API_SECRET_KEY=<openssl rand -hex 32>`
- SWA: `VITE_API_KEY=<위와 동일한 값>`

---

### 4. Private Endpoint (보류 권장)

**현재:** External ingress — 누구나 Container Apps URL 접근 가능.

**구현 제약:** Container Apps에 Private Endpoint를 적용하려면 VNet-integrated Environment 재생성이 필요.
기존 환경 인플레이스 전환 불가 → 다운타임 발생하는 파괴적 변경.

**비용:** 약 $8/월 (Private Endpoint + Private DNS Zone)

**권장 결정:** 항목 2(SWA 프록시)로 URL을 은폐하고 항목 5(IP 화이트리스트)로 직접 접근을 차단하면
Private Endpoint의 목적을 무비용으로 달성 가능. 외부 서비스화 또는 컴플라이언스 요구 시 재검토.

---

### 5. IP 화이트리스트

**방법 A (인프라 레벨): Azure Container Apps 인그레스 IP 제한 — 무료, 권장**

```bash
# SWA 아웃바운드 IP 확인 후 (Portal → SWA → Overview → Outbound IP addresses)
az containerapp ingress access-restriction set \
  --name sohobi-backend \
  --resource-group <RG_NAME> \
  --rule-name "allow-swa" \
  --ip-address <SWA_IP>/32 \
  --action Allow
# (SWA 아웃바운드 IP 각각 반복, 개발팀 IP도 추가)
```

**방법 B (애플리케이션 레벨): FastAPI 미들웨어 — `api_server.py`에 추가 (심층 방어)**
```python
class IPFilterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_ips):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips)

    async def dispatch(self, request, call_next):
        if not self.allowed_ips:
            return await call_next(request)
        forwarded = request.headers.get("X-Forwarded-For", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "")
        if client_ip not in self.allowed_ips:
            return JSONResponse(status_code=403, content={"error": "접근 제한"})
        return await call_next(request)

_allowed_ips_raw = os.getenv("ALLOWED_IPS", "")
_allowed_ips = [ip.strip() for ip in _allowed_ips_raw.split(",") if ip.strip()]
if _allowed_ips:
    app.add_middleware(IPFilterMiddleware, allowed_ips=_allowed_ips)
```

**Container Apps 환경변수:** `ALLOWED_IPS=<SWA IP1>,<SWA IP2>,...`

---

## 우선순위 실행 순서

### Phase 1 — 즉시 (코드 변경, 무료, 약 2시간)

| 순위 | 작업 | 파일 |
|------|------|------|
| 1 | CORS origin 화이트리스트 수정 | `api_server.py:48-54` |
| 2 | `auth.py` 생성 + 모든 엔드포인트에 인증 적용 | `auth.py` (신규), `api_server.py` |
| 3 | SWA 프록시 설정 + 프론트엔드 BASE_URL 상대경로 전환 | `staticwebapp.config.json`, `frontend/src/api.js` |
| 4 | IP 필터 미들웨어 추가 | `api_server.py` |

### Phase 2 — 단기 (Azure 설정, 무료, 약 30분)

| 순위 | 작업 | 방법 |
|------|------|------|
| 5 | Container Apps 인그레스 IP 화이트리스트 | Azure Portal 또는 CLI |
| 6 | 환경변수 등록 (API_SECRET_KEY, ALLOWED_IPS, CORS_EXTRA_ORIGINS) | Container Apps + SWA |

### Phase 3 — 보류 (비용 발생 또는 파괴적 변경)

- Private Endpoint: 외부 서비스화 또는 컴플라이언스 요구 시
- Azure APIM: 트래픽 > 100만 req/월 또는 정교한 rate limiting 필요 시

---

## 환경변수 체크리스트

### Container Apps

```
API_SECRET_KEY=<openssl rand -hex 32>
CORS_EXTRA_ORIGINS=
ALLOWED_IPS=<SWA 아웃바운드 IP 목록, 쉼표 구분>
```

### Azure Static Web Apps

```
VITE_API_KEY=<API_SECRET_KEY와 동일>
VITE_API_URL=  (SWA 프록시 전환 후 제거)
```

---

## 수정 대상 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/api_server.py` | CORS 수정, IP 미들웨어 추가, 엔드포인트 인증 의존성 추가 |
| `integrated_PARK/auth.py` | 신규 생성 — API Key 검증 |
| `frontend/staticwebapp.config.json` | routes 프록시 규칙 + globalHeaders 추가 |
| `frontend/src/api.js` | BASE_URL 상대경로 전환, X-API-Key 헤더 추가 |

---

## 검증 방법

```bash
# 1. 외부에서 직접 호출 → 401 (인증 없음)
curl -X POST https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/query \
  -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 401

# 2. 잘못된 API Key → 401
curl -X POST https://sohobi-backend.../api/v1/query \
  -H "X-API-Key: wrong" -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 401

# 3. IP 화이트리스트 설정 후 외부 IP → 403
curl -X POST https://sohobi-backend.../api/v1/query
# 기대: 403

# 4. SWA 프록시 통한 정상 요청 → 200
curl -X POST https://sohobi.net/api/v1/query \
  -H "X-API-Key: <correct key>" -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 200

# 5. /api/v1/logs 인증 없이 접근 → 401
curl https://sohobi-backend.../api/v1/logs
# 기대: 401
```
