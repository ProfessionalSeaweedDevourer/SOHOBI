# 인수인계 문서 — 2026-04-07 (VWorld 공시지가 & WMS 레이어 복구)

## 브랜치 / PR 현황

| PR | 제목 | 상태 |
|----|------|------|
| #193 | fix: 공시지가 VWorld API 에러 로깅 강화 | ✅ merged |
| #194 | fix: VWorld WMS DOMAIN 파라미터 sohobi.net 적용 | ✅ merged |
| **#195** | **fix: VWorld Data API domain 파라미터 추가 — 공시지가 인증 수정** | **🔴 open — 미머지** |

**다음 세션 첫 작업: PR #195 머지 후 배포 대기 → TC 실행.**

---

## 이번 세션에서 해결한 것

### ✅ Bug 1 — 지적도/관광 WMS 레이어 실종 (PR #194)

**원인:** WOO가 VWorld API 키 등록 도메인을 `localhost:5173` → `https://sohobi.net`으로 변경했으나 `Layerpanel.jsx`에 `DOMAIN=localhost` 하드코딩.

**수정:** `DOMAIN` 파라미터를 `VITE_VWORLD_DOMAIN` 환경변수로 교체, `.env.production`과 SWA 워크플로우에 `https://sohobi.net` 주입.

**결과:** 지적도·관광 WMS 레이어 및 학교·관광 마커 모두 정상 복구 확인.

---

### 🔴 Bug 2 — 공시지가 항상 "없음" (PR #195 — 미배포)

**아키텍처 분석:**

```
[브라우저 sohobi.net/map]
  ↓ fetch /realestate/land-value?pnu=xxx
[Azure Container Apps 백엔드]
  ↓ GET https://api.vworld.kr/req/data?...&key=BE3AF...
      ← INCORRECT_KEY (domain 파라미터 없음)
  ↓ data: []
[프론트엔드] → "공시지가 정보 없음"
```

VWorld API 키 인증 방식: **도메인 기반** (`https://sohobi.net` 등록).
WMS 프록시는 `DOMAIN=https://sohobi.net` 파라미터 포함 → 인증 성공.
Data API(`/req/data`)는 `domain` 파라미터 누락 → `INCORRECT_KEY` → `data: []`.

**수정 내용 (PR #195):**

| 파일 | 변경 |
|------|------|
| `integrated_PARK/db/dao/landValueDAO.py` | `__init__`에 `self._domain = os.getenv("VWORLD_DOMAIN", "https://sohobi.net")` 추가, URL에 `&domain={self._domain}` 삽입 |
| `integrated_PARK/.env.example` | `VWORLD_DOMAIN=https://sohobi.net` 문서화 |
| `.github/workflows/deploy-backend.yml` | `--set-env-vars`에 `VWORLD_DOMAIN=https://sohobi.net` 추가 |

---

## 수정 파일 목록

```
frontend/src/components/map/panel/Layerpanel.jsx   ← DOMAIN 환경변수화
frontend/.env.production                            ← VITE_VWORLD_DOMAIN=https://sohobi.net
.github/workflows/azure-static-web-apps-*.yml      ← 빌드 env 주입
integrated_PARK/db/dao/landValueDAO.py             ← domain 파라미터 + 에러 로깅 강화
integrated_PARK/.env.example                        ← VWORLD_DOMAIN 문서화
.github/workflows/deploy-backend.yml               ← 백엔드 env 주입
```

---

## 다음 세션 인수사항 (우선순위 순)

### 1. PR #195 머지 및 TC 실행 (필수)

머지 후 약 3~5분 Azure 배포 대기, 이후:

```bash
source integrated_PARK/.env

# TC1: 공시지가 API 직접 호출
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/realestate/land-value?pnu=1114016200102490069" \
  | python3 -m json.tool
# 기대값: data 배열에 연도별 공시지가 값 존재

# TC2: 백엔드 에러 로그 확인
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=errors&limit=20" \
  | python3 -m json.tool | grep -i "vworld\|LandValue"
# 기대값: [LandValueDAO] VWorld ERROR 없음
```

TC3: `sohobi.net/map` → 신당동 지적도 클릭 → 팝업 공시지가 금액 표시 확인.

### 2. TC 실패 시 대응 분기

| 실패 유형 | 원인 | 조치 |
|-----------|------|------|
| `data: []` 지속, 에러 로그 없음 | 해당 필지 BUBUN 데이터 미존재 | `LP_PA_CBND_PLL` 데이터셋 fallback 추가 |
| `VWorld ERROR code=INCORRECT_KEY` | domain 파라미터가 VWorld에 미적용 | `.env` VWORLD_DOMAIN 확인, 배포 환경변수 재확인 |
| `VWorld ERROR code=NOT_FOUND` | 해당 연도 데이터 없음 | 정상 케이스 |

### 3. LP_PA_CBND_PLL fallback (선택적 개선)

`LP_PA_CBND_BUBUN`은 부분경계(sub-lot) 레이어. PNU 마지막 4자리가 `0000`인 본번 필지는 이 데이터셋에 없을 수 있음. 인증 수정 후에도 일부 필지에서 `data: []`가 지속되면 `LP_PA_CBND_PLL` 데이터셋으로 재조회하는 fallback을 `landValueDAO.py`에 추가해야 함.

---

## 관련 파일 참조

| 파일 | 역할 |
|------|------|
| `frontend/src/components/map/panel/Layerpanel.jsx` | VWorld WMS 레이어 생성 (`makeWmsLayer`, `makeCadastralLayer`) |
| `frontend/src/hooks/map/useMap.js` | VWorld WMTS 기본지도 타일 (브라우저 직접 호출) |
| `integrated_PARK/db/dao/landValueDAO.py` | VWorld Data API 공시지가 조회 |
| `integrated_PARK/realestate_router.py` | `/realestate/land-value` 엔드포인트 |
| `integrated_PARK/api_server.py:694` | `/wms/{path}` VWorld WMS 프록시 |

## VWorld 인증 구조 요약 (아키텍처 메모)

```
VWorld API 키: BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF
등록 방식: 도메인 기반 (https://sohobi.net)
등록자: WOO (TerryBlackhoodWoo)

호출 경로별 인증 처리:
  WMTS (기본지도)  → 브라우저 직접 호출 → Referer: https://sohobi.net → ✅
  WMS (레이어)     → 백엔드 프록시 → DOMAIN=https://sohobi.net 파라미터 → ✅
  Data API (공시지가) → 백엔드 직접 호출 → domain=https://sohobi.net 파라미터 → ✅ (PR #195 후)
```
