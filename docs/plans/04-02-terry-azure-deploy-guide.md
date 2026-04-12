# TERRY 지도 서버 Azure 배포 가이드

> **대상 독자:** TERRY 서버(`mapController`, `realEstateController`) Azure 배포 담당자
> **작성일:** 2026-04-02

---

## 1. 개요

TERRY 백엔드는 두 개의 FastAPI 서버로 구성됩니다.

| 서버 | 파일 | 역할 |
|------|------|------|
| Map API | `TERRY/p01_backEnd/mapController.py` | 상가 위치·반경 검색 (`/map/*`) |
| RealEstate API | `TERRY/p01_backEnd/realEstateController.py` | 상권 매출·점포수·실거래가 (`/realestate/*`) |

두 서버 모두 **사내 Oracle DB** (`<ORACLE_HOST>:1521/xe`)에 접속합니다.
Azure에서 이 IP로 직접 연결이 불가능하므로, 아래 **2번 단계를 반드시 먼저 해결해야 합니다.**

---

## 2. ⚠️ Oracle DB 접근 문제 해결 (필수)

현재 Oracle 연결 정보가 코드에 하드코딩되어 있습니다.

```python
# TERRY/p01_backEnd/DAO/fable/oracleDBConnect.py
DB_INFO = "<ORACLE_USER>/<ORACLE_PASSWORD>@//<ORACLE_HOST>:1521/xe"  # ← 사내 IP, Azure에서 접근 불가
```

### 해결 방법 (3가지 중 선택)

#### 방법 A — Azure VPN으로 사내 Oracle 연결 (권장, 데이터 마이그레이션 불필요)

1. Azure Portal → **Virtual Network Gateway** 또는 **ExpressRoute** 설정
2. 사내 네트워크와 Azure VNet을 VPN으로 연결
3. Oracle DB 서버(`<ORACLE_HOST>`)가 Azure에서 접근 가능한 프라이빗 IP로 라우팅되는지 확인
4. 아래 "환경변수화" 작업 후 `ORACLE_HOST`에 해당 IP 입력

> **장점:** 데이터 이전 불필요, 기존 Oracle 그대로 사용
> **단점:** VPN 비용 발생, 네트워크 팀 협력 필요

---

#### 방법 B — Oracle을 Azure VM에 재설치

1. Azure VM 생성 (OS: Oracle Linux 또는 Ubuntu)
2. Oracle DB XE 설치 및 기존 데이터 덤프(expdp) → 임포트(impdp)
3. `ORACLE_HOST`에 VM의 프라이빗 IP 입력

> **장점:** 완전 클라우드 환경
> **단점:** Oracle 라이선스 및 VM 비용, 마이그레이션 작업 필요

---

#### 방법 C — Oracle 데이터를 Azure PostgreSQL로 마이그레이션 (장기 권장)

상권 매출·점포수 데이터(`SANGKWON_SALES`, `SANGKWON_STORE`)는 이미 Azure PostgreSQL에 적재되어 있습니다.
`integrated_PARK/db/export_oracle_to_csv.py`를 사용해 나머지 테이블도 PostgreSQL로 이전하면,
별도 서버 배포 없이 통합 API 서버에서 모든 기능을 제공할 수 있습니다.

이전이 필요한 테이블:
- `STORE_SEOUL` (개별 상가 위치 정보)
- `LAW_ADM_MAP` (행정동 ↔ 법정동 매핑)
- `LAW_DONG_SEOUL` (법정동 코드 정보)
- `SVC_INDUTY_MAP` (업종 대분류 매핑)

> **장점:** 서버 추가 없이 기존 통합 API에서 처리 가능
> **단점:** 초기 마이그레이션 작업 필요

---

## 3. 사전 준비 작업

### 3-1. Oracle 연결을 환경변수로 변경

`TERRY/p01_backEnd/DAO/fable/oracleDBConnect.py`를 수정합니다.

**수정 전:**
```python
DB_INFO = "<ORACLE_USER>/<ORACLE_PASSWORD>@//<ORACLE_HOST>:1521/xe"
```

**수정 후:**
```python
import os

_user     = os.getenv("ORACLE_USER", "shobi")
_password = os.getenv("ORACLE_PASSWORD", "8680")
_host     = os.getenv("ORACLE_HOST", "<ORACLE_HOST>")
_port     = os.getenv("ORACLE_PORT", "1521")
_sid      = os.getenv("ORACLE_SID", "xe")
DB_INFO   = f"{_user}/{_password}@//{_host}:{_port}/{_sid}"
```

### 3-2. requirements.txt 작성

`TERRY/p01_backEnd/requirements.txt` 파일 생성:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
oracledb==2.3.0
httpx==0.27.2
pandas==2.2.2
python-dotenv==1.0.1
```

> 실제 사용 버전과 다를 경우 `.venv/bin/pip freeze`로 확인 후 맞추세요.

### 3-3. Dockerfile 작성

`TERRY/p01_backEnd/` 아래에 두 개의 Dockerfile을 작성합니다.

**Dockerfile.map** (mapController용):
```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app

# oracledb thin mode는 libaio 불필요 (Python-only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8681

CMD ["sh", "-c", "uvicorn mapController:app --host 0.0.0.0 --port ${PORT:-8681} --workers 1"]
```

**Dockerfile.realestate** (realEstateController용):
```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8682

CMD ["sh", "-c", "uvicorn realEstateController:app --host 0.0.0.0 --port ${PORT:-8682} --workers 1"]
```

---

## 4. Azure 리소스 구성

### 4-1. Azure Container Registry (ACR) 확인

기존 `integrated_PARK` 배포에 사용하는 ACR을 그대로 사용합니다.
ACR 이름을 모르면 Azure Portal → Container Registries에서 확인하세요.

```bash
# ACR 로그인 (예: ACR 이름이 sohobiregistry 인 경우)
az acr login --name <ACR이름>
```

### 4-2. 이미지 빌드 및 푸시

`TERRY/p01_backEnd/` 디렉토리에서 실행합니다.

```bash
cd TERRY/p01_backEnd

# Map API 이미지
docker build -f Dockerfile.map -t <ACR이름>.azurecr.io/sohobi-map-api:latest .
docker push <ACR이름>.azurecr.io/sohobi-map-api:latest

# RealEstate API 이미지
docker build -f Dockerfile.realestate -t <ACR이름>.azurecr.io/sohobi-realestate-api:latest .
docker push <ACR이름>.azurecr.io/sohobi-realestate-api:latest
```

### 4-3. Azure Container Apps 생성

기존 `sohobi-backend`와 동일한 **Container Apps Environment**를 사용합니다.
환경 이름 확인: `az containerapp env list -o table`

```bash
# 환경변수 파일 준비 (아래 5번 참조 후 실행)

# Map API 앱 생성
az containerapp create \
  --name sohobi-map-api \
  --resource-group <리소스그룹명> \
  --environment <Container Apps 환경명> \
  --image <ACR이름>.azurecr.io/sohobi-map-api:latest \
  --registry-server <ACR이름>.azurecr.io \
  --target-port 8681 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --env-vars \
      ORACLE_HOST=<Oracle서버IP> \
      ORACLE_PORT=1521 \
      ORACLE_SID=xe \
      ORACLE_USER=shobi \
      ORACLE_PASSWORD=secretref:oracle-password

# RealEstate API 앱 생성
az containerapp create \
  --name sohobi-realestate-api \
  --resource-group <리소스그룹명> \
  --environment <Container Apps 환경명> \
  --image <ACR이름>.azurecr.io/sohobi-realestate-api:latest \
  --registry-server <ACR이름>.azurecr.io \
  --target-port 8682 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --env-vars \
      ORACLE_HOST=<Oracle서버IP> \
      ORACLE_PORT=1521 \
      ORACLE_SID=xe \
      ORACLE_USER=shobi \
      ORACLE_PASSWORD=secretref:oracle-password \
      SEOUL_API_KEY=<서울API키>
```

> `secretref:oracle-password`는 Azure Container Apps Secret으로 비밀번호를 관리하는 방식입니다.
> Secret 추가: `az containerapp secret set --name sohobi-realestate-api ... --secrets oracle-password=<실제비밀번호>`

배포 후 각 앱의 URL 확인:
```bash
az containerapp show --name sohobi-map-api --resource-group <리소스그룹명> \
  --query properties.configuration.ingress.fqdn -o tsv

az containerapp show --name sohobi-realestate-api --resource-group <리소스그룹명> \
  --query properties.configuration.ingress.fqdn -o tsv
```

---

## 5. 환경변수 목록

### Map API (`mapController.py`)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `ORACLE_HOST` | Oracle 서버 호스트 | `<ORACLE_HOST>` 또는 Azure VM IP |
| `ORACLE_PORT` | Oracle 포트 | `1521` |
| `ORACLE_SID` | Oracle SID | `xe` |
| `ORACLE_USER` | Oracle 사용자 | `shobi` |
| `ORACLE_PASSWORD` | Oracle 비밀번호 | (Secret으로 관리) |

### RealEstate API (`realEstateController.py`)

위 Oracle 변수에 추가로:

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `SEOUL_API_KEY` | 서울 열린데이터광장 API 키 | (기존 .env 참조) |

> `SEOUL_API_KEY`가 현재 코드에서 환경변수로 처리되지 않는다면 `seoulRtmsDAO.py`의 `SEOUL_RTMS_KEY` 하드코딩 부분도 환경변수로 교체 필요.

---

## 6. 프론트엔드 Azure 빌드 변수 업데이트

Container Apps 배포 후 발급된 URL을 Azure Static Web Apps 빌드 변수에 설정합니다.

Azure Portal → Static Web Apps → `sohobi 프론트엔드 앱` → **Configuration** → **Application settings**:

| 이름 | 값 |
|------|-----|
| `VITE_MAP_URL` | `https://sohobi-map-api.<환경도메인>.azurecontainerapps.io` |
| `VITE_REALESTATE_URL` | `https://sohobi-realestate-api.<환경도메인>.azurecontainerapps.io` |

설정 후 **재배포(Redeploy)** 또는 새 커밋 푸시로 프론트엔드를 다시 빌드합니다.

---

## 7. CORS 설정 확인

`mapController.py`와 `realEstateController.py`의 `allow_origins` 목록에 프론트엔드 도메인이 포함되어 있는지 확인합니다.

```python
# 두 파일 모두 아래 항목 추가 필요
allow_origins=[
    "https://sohobi.net",
    "https://www.sohobi.net",
    "https://<SWA_RESOURCE_NAME>.6.azurestaticapps.net",
    # 기존 로컬 주소는 유지해도 무방
]
```

---

## 8. 배포 후 동작 검증

```bash
# Map API 확인
curl "https://sohobi-map-api.<도메인>/map/stores-by-dong?adm_cd=11680640"

# RealEstate API 확인
curl "https://sohobi-realestate-api.<도메인>/realestate/sangkwon?adm_cd=11680640"
curl "https://sohobi-realestate-api.<도메인>/realestate/sangkwon-store?adm_cd=11680640"
curl "https://sohobi-realestate-api.<도메인>/realestate/sangkwon-quarters"
```

정상 응답 시 프론트엔드 지도 화면에서:
- 동 클릭 → 매출 패널 데이터 표시 ✅
- 점포수 탭 전환 → 업종별 점포 데이터 표시 ✅
- 상가 마커 팝업 → 업종별 상가 목록 표시 ✅

---

## 9. 참고: 현재 임시 해결책과의 관계

이 서버를 배포하기 전까지는, `integrated_PARK/map_router.py`(2026-04-02 추가)가
Azure PostgreSQL 기반으로 매출·점포수 데이터를 제공하고 있습니다.
TERRY 서버 배포 완료 후 `frontend/.env.production`의 `VITE_MAP_URL`, `VITE_REALESTATE_URL`을
TERRY 서버 URL로 교체하면 됩니다 (개별 상가 팝업 등 전체 기능 복원).
