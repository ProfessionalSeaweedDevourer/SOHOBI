# 백엔드 보안 강화 — 적용 내역 및 팀원 가이드

> 작성일: 2026-03-30
> 브랜치: PARK
> 대상 서비스: `integrated_PARK/` (Azure Container Apps) + `frontend/` (Azure Static Web Apps)

---

## 배경

프론트엔드(sohobi.net)에서 백엔드(Azure Container Apps)를 직접 호출하는 구조상,
백엔드 URL이 브라우저 개발자도구 Network 탭에 노출된다.
기존 백엔드는 인증·접근 제한이 전혀 없어 누구나 API를 직접 호출할 수 있는 상태였다.
이번 커밋에서 아래 5가지 항목을 보완하였다.

---

## 적용 내역

### 1. CORS 화이트리스트 (`integrated_PARK/api_server.py`)

**변경 전:** `allow_origins=["*"]` — 모든 origin 허용
**변경 후:** 허용 origin을 명시적으로 지정

```
허용 origin:
  https://sohobi.net
  https://www.sohobi.net
  https://delightful-rock-0de6c000f.6.azurestaticapps.net
  + CORS_EXTRA_ORIGINS 환경변수에 쉼표 구분으로 추가 가능
```

> **참고:** CORS는 브라우저 전용 메커니즘이다. `curl` 등 non-browser 클라이언트는 CORS 헤더를 무시하므로, 이것만으로는 직접 API 호출을 막을 수 없다. API Key 인증(항목 3)과 함께 사용해야 한다.

---

### 2. SWA 역방향 프록시 (`frontend/staticwebapp.config.json`)

Azure Static Web Apps의 내장 프록시 기능을 이용해 `/api/*` 경로를 Container Apps로 전달한다.

```
브라우저 → sohobi.net/api/v1/query
                   ↓ (SWA 서버사이드 프록시)
         Container Apps /api/v1/query
```

**효과:** 브라우저 개발자도구에 Container Apps URL이 노출되지 않는다.

**추가된 보안 헤더:**

| 헤더 | 값 | 의미 |
|------|----|------|
| `X-Content-Type-Options` | `nosniff` | MIME 스니핑 차단 |
| `X-Frame-Options` | `DENY` | 클릭재킹 차단 |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS 강제 (1년) |

---

### 3. API Key 인증 (`integrated_PARK/auth.py` 신규, `api_server.py` 수정)

**보호 대상 엔드포인트 (전부):**

| 엔드포인트 | 메서드 | 기존 | 변경 후 |
|-----------|--------|------|---------|
| `/api/v1/query` | POST | 무인증 개방 | API Key 필수 |
| `/api/v1/stream` | POST | 무인증 개방 | API Key 필수 |
| `/api/v1/signoff` | POST | 무인증 개방 | API Key 필수 |
| `/api/v1/doc/chat` | POST | 무인증 개방 | API Key 필수 |
| `/api/v1/logs` | GET | **무인증 개방** ← 특히 위험 | API Key 필수 |
| `/api/v1/logs/export` | GET | EXPORT_SECRET (기존 유지) | 기존 유지 |
| `/health` | GET | 개방 | 개방 (의도적) |

**인증 방식:** 요청 헤더에 아래 중 하나를 포함한다.

```http
X-API-Key: <API_SECRET_KEY 값>
```

또는

```http
Authorization: Bearer <API_SECRET_KEY 값>
```

**개발 모드 (환경변수 미설정 시):** `API_SECRET_KEY`가 설정되지 않으면 인증을 완전히 건너뛴다.
로컬에서 `.env`에 이 값을 추가하지 않으면 기존과 동일하게 `curl` 테스트, 스트레스 테스트 모두 통과한다.

---

### 4. IP 화이트리스트 미들웨어 (`integrated_PARK/api_server.py`)

**개발 모드 (환경변수 미설정 시):** `ALLOWED_IPS`가 비어있으면 미들웨어가 비활성화된다.

**프로덕션 활성화:** `ALLOWED_IPS` 환경변수에 허용할 IP를 쉼표로 구분하여 지정한다.

```
ALLOWED_IPS=20.10.x.x,20.10.y.y,20.10.z.z,...
```

차단된 IP는 `sohobi.security` 로거에 `IP_BLOCKED` 경고로 기록된다.

> **Azure 인프라 레벨 추가 설정 (권장):** Azure Portal → Container Apps → Settings → Ingress →
> IP Security Restrictions에서도 동일하게 SWA 아웃바운드 IP를 등록하면 애플리케이션 코드에 도달하기 전에 차단된다.
> SWA 아웃바운드 IP는 Portal → Static Web App → Overview → Outbound IP addresses에서 확인한다.

---

### 5. Private Endpoint (미적용 — 보류)

Container Apps에 Private Endpoint를 적용하려면 VNet-integrated Environment를 새로 생성해야 한다(기존 환경 인플레이스 전환 불가, 다운타임 발생). 비용 약 $8/월.

**현재 결정:** SWA 프록시(항목 2) + IP 화이트리스트(항목 4)의 조합으로 동일한 목적(외부에서 Container Apps URL 직접 접근 차단)을 무비용으로 달성 가능하다. 외부 서비스화 또는 컴플라이언스 요구 발생 시 재검토한다.

---

## 팀원이 할 일 — 프로덕션 배포 전 필수 환경변수 등록

### Container Apps (Azure Portal → sohobi-backend → Settings → Environment variables)

| 변수명 | 값 | 비고 |
|--------|-----|------|
| `API_SECRET_KEY` | `openssl rand -hex 32` 결과 | 강력한 랜덤값 사용 |
| `CORS_EXTRA_ORIGINS` | _(빈 문자열)_ | 로컬 개발 시에는 `http://localhost:5173` 추가 가능 |
| `ALLOWED_IPS` | SWA 아웃바운드 IP 목록 (쉼표 구분) | Portal에서 확인 후 입력 |

### Azure Static Web Apps (Portal → sohobi-frontend → Settings → Environment variables)

| 변수명 | 값 | 비고 |
|--------|-----|------|
| `VITE_API_URL` | _(빈 문자열)_ | SWA 프록시 경유 시 빈 값, 로컬 개발 시 `http://localhost:8000` |
| `VITE_API_KEY` | `API_SECRET_KEY`와 동일한 값 | 프론트엔드에서 X-API-Key 헤더로 전송 |

> **주의:** 두 값이 다르면 모든 API 호출이 401로 실패한다.

---

## 로컬 개발 환경 설정 (`integrated_PARK/.env`)

보안 기능을 로컬에서 비활성화하려면 `.env`에 해당 변수를 추가하지 않거나 빈 값으로 둔다.

```dotenv
# API Key 인증 비활성화 (로컬 개발용)
# API_SECRET_KEY=         ← 주석 처리하거나 아예 없으면 인증 건너뜀

# IP 필터 비활성화
# ALLOWED_IPS=            ← 주석 처리하거나 빈 값이면 필터 비활성화

# 로컬 프론트엔드 origin 추가 (필요 시)
CORS_EXTRA_ORIGINS=http://localhost:5173
```

프론트엔드 로컬 개발 (`.env.local` 또는 `.env`):

```dotenv
VITE_API_URL=http://localhost:8000
# VITE_API_KEY=           ← 백엔드 API_SECRET_KEY 미설정 시 프론트엔드도 없어도 됨
```

---

## 검증 방법

### 프로덕션 배포 후 확인 순서

```bash
# 1. 인증 없이 직접 호출 → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/query \
  -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 401

# 2. 잘못된 API Key → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/query \
  -H "X-API-Key: wrong" -H "Content-Type: application/json" -d '{"question":"test"}'
# 기대: 401

# 3. IP 화이트리스트 설정 후 외부에서 직접 호출 → 403
# (SWA 아웃바운드 IP가 아닌 로컬 PC에서 실행)
# 기대: 403

# 4. SWA 프록시 경유 정상 호출 → 200
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://sohobi.net/api/v1/query \
  -H "X-API-Key: <실제 키>" -H "Content-Type: application/json" -d '{"question":"테스트"}'
# 기대: 200

# 5. /api/v1/logs 인증 없이 → 401
curl -s -o /dev/null -w "%{http_code}" \
  https://sohobi-backend.livelybay-7bc24b2f.koreacentral.azurecontainerapps.io/api/v1/logs
# 기대: 401
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/api_server.py` | CORS 화이트리스트, IP 필터 미들웨어, 엔드포인트 인증 의존성 |
| `integrated_PARK/auth.py` | 신규 — API Key 검증 의존성 함수 |
| `frontend/staticwebapp.config.json` | SWA 역방향 프록시, 보안 헤더 |
| `frontend/src/api.js` | `VITE_API_URL` 상대경로 대응, `X-API-Key` 헤더 전송 |
