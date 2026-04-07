# 사고 보고서 — 2026-04-07 (지도 API 전면 401 비상 복구 + 워크플로우 버그 근본 수정)

## 브랜치 / PR 현황

| PR | 제목 | 상태 |
|----|------|------|
| #195 | fix: VWorld Data API domain 파라미터 추가 | ✅ merged + 배포 완료 |
| #197 | ci: 프론트엔드 VITE_API_KEY 재빌드 트리거 (비상 복구) | ✅ merged + **SWA 빌드 성공** |
| **#196** | **지도 main 통합작업** (WOO-clean2, TerryBlackhoodWoo) | **🔴 open — 머지 전 수정 필요** |

---

## 이번 세션 작업 요약

### ✅ PR #195 이미 배포 완료 확인

공시지가 VWorld domain 파라미터 fix, 세션 시작 전 완료 상태.

---

### 🔴 지도 API 전면 401 비상 복구 (PR #197)

**원인:**
```
T1: GitHub Secrets에서 API_SECRET_KEY + VITE_API_KEY 동시 갱신
T2: PR #195 백엔드 재배포 → 신 키(B)로 컨테이너 기동
    → 기존 프론트엔드(PR #194 빌드, 구 키 A 주입) 전 API 401
```

**증거:**
- 콘솔 로그에서 초기 `stores-by-dong` 3회 성공 = PR #195 배포 중 구 컨테이너 응답
- 이후 `sangkwon`, `festivals`, `sangkwon-svc`, `stores-by-dong` 전부 401
- 로컬 `.env`의 API_SECRET_KEY로 curl → 401 (로컬 키 = 구 키)

**조치:** PR #197 (docs 커밋) → main 머지 → SWA Build and Deploy Job → ✅ 성공 (1m9s)

---

### 🔴 추가 발견 — deploy-backend.yml 인자 포맷 버그 (미수정)

PR #195의 `deploy-backend.yml` 변경이 `API_SECRET_KEY`를 컨테이너에서 깨뜨렸음.

```yaml
# 버그 (PR #195 현재 상태):
--set-env-vars "API_SECRET_KEY=${{ secrets.API_SECRET_KEY }} VWORLD_DOMAIN=https://sohobi.net"
# Azure CLI는 따옴표 안 전체를 하나의 인자로 파싱 → split("=", 1) 결과:
#   key   = "API_SECRET_KEY"
#   value = "ed6edd5cf8... VWORLD_DOMAIN=https://sohobi.net"  ← 쓰레기 값!
# VWORLD_DOMAIN은 아예 설정 안 됨 (default "https://sohobi.net" 사용 → 우연히 동작)

# 수정 필요:
--set-env-vars "API_SECRET_KEY=${{ secrets.API_SECRET_KEY }}" "VWORLD_DOMAIN=https://sohobi.net"
```

**영향:** 컨테이너의 `API_SECRET_KEY` ≠ 실제 시크릿 값 → 모든 인증 실패 (401)
→ PR #197 SWA 재빌드만으로는 복구 불완전. **백엔드도 재배포 필요.**

**주의:** API 키 갱신 시 반드시 프론트엔드 재빌드 필요 (자동 트리거 없음).

---

## PR #196 코드 리뷰 (WOO-clean2 → main)

### 변경 범위

| 파일 | 변경 | 비고 |
|------|------|------|
| `frontend/src/components/map/MapView.jsx` | +245/-180 | 대규모 리팩터 |
| `frontend/src/components/map/panel/DongPanel.jsx` | +1028/-77 | 서브컴포넌트 9개 통합 |
| `frontend/src/components/map/panel/DongPanel/` 전체 | 삭제 | BarRow, GenderDonut 등 |
| `frontend/src/components/map/panel/Layerpanel.jsx` | +126/-115 | WMS 레이어 생성 재구성 |
| `frontend/src/hooks/map/useMapSetup.js` | 신규 | 줌 추적 + 지적도 초기화 훅 분리 |
| `frontend/src/hooks/map/useMarkers.js` | +54/-54 | |
| `frontend/src/hooks/map/useLandmarkLayer.js` | +34/-14 | |
| `frontend/vite.config.js` | +23/-2 | 프록시 경로 추가 |
| `integrated_PARK/db/dao/landmarkDAO.py` | +5/-5 | 타입 캐스트 버그 수정 |
| `integrated_PARK/map_data_router.py` | +2/-2 | 랜드마크 limit 500→2000 |

---

### 🔴 Blocking — 머지 전 필수 수정

**`frontend/src/hooks/map/useMapSetup.js` 52번째 줄:**

```js
// 🔴 현재 (WOO-clean2)
url: `/wms/req/wms?KEY=${vKey}&DOMAIN=localhost`,

// ✅ 수정 필요 (PR #194와 동일하게)
url: `/wms/req/wms?KEY=${vKey}&DOMAIN=${import.meta.env.VITE_VWORLD_DOMAIN || "localhost"}`,
```

이 한 줄이 수정되지 않으면 **PR #194에서 고친 WMS 지적도 레이어 버그가 재발**합니다.
(`Layerpanel.jsx`는 이미 `VITE_VWORLD_DOMAIN` 사용 — OK)

---

### ✅ 긍정적 변경 사항

**MapView.jsx — WMS→백엔드 API fallback (신규):**
```js
if (!wmsResult.landValue && wmsResult.parsed.pnu) {
    // WMS GetFeatureInfo에서 공시지가 없을 때 백엔드 REST API 재조회
    fetch(`${REALESTATE_URL}/realestate/land-value?pnu=...`)
}
```
→ PR #195에서 고친 백엔드 API를 실제로 활용하는 로직. 좋은 개선.

**`landmarkDAO.py` — 타입 캐스트 버그 수정:**
```python
# 전: content_type_id IN (%(t0)s, ...)  — varchar vs int 불일치
# 후: content_type_id::integer IN (...)
```

**`vite.config.js` — 누락 프록시 추가:**
`/map/landmarks`, `/map/schools`, `/map/festivals` 로컬 개발 프록시 추가 (기존 없었음).

---

### ⚠️ 검토 필요

- `DongPanel.jsx` +1028줄 — UI 동작 확인 필요 (데이터 표시, 분기 전환 등)
- `MapView.jsx` 대규모 리팩터 — 마커 이동 버그 수정됐는지 확인 (WOO 커밋 메시지 참조)

---

## 다음 세션 인수사항 (우선순위 순)

### 1. 🔴 deploy-backend.yml 1줄 수정 + 백엔드 재배포 (최우선)

```yaml
# .github/workflows/deploy-backend.yml 64번 줄 수정:
# 전:
--set-env-vars "API_SECRET_KEY=${{ secrets.API_SECRET_KEY }} VWORLD_DOMAIN=https://sohobi.net"
# 후:
--set-env-vars "API_SECRET_KEY=${{ secrets.API_SECRET_KEY }}" "VWORLD_DOMAIN=https://sohobi.net"
```

수정 후 PARK→main PR 머지 → `deploy-backend.yml` 경로 변경 감지 → 백엔드 재배포.
재배포 완료 후 컨테이너에 올바른 `API_SECRET_KEY` 적용.

### 2. TC 실행 — 복구 검증 (백엔드 재배포 완료 후)

```bash
source integrated_PARK/.env

# TC1: API 직접 호출 (백엔드 재배포 후 로컬 키로 동작해야 함)
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/realestate/land-value?pnu=1114016200102490069" \
  | python3 -m json.tool

# TC3: sohobi.net/map → 신당동 클릭 → 매출/점포수 데이터 표시 여부
```

### 3. PR #196 수정 요청 (WOO에게)

`useMapSetup.js` 52번 줄 `DOMAIN=localhost` → `VITE_VWORLD_DOMAIN` 수정 후 머지.
수정 1줄이므로 WOO가 직접 수정하거나 PARK에서 수정 후 승인 요청.

### 3. 로컬 `.env` 동기화

`integrated_PARK/.env`의 `API_SECRET_KEY` = 구 키 (서버와 불일치).
→ curl 테스트 불가. 시크릿 관리자에게 현재 키 확인 요청.

### 4. LP_PA_CBND_PLL fallback (TC 후 판단)

TC에서 공시지가 "없음" 지속 시 구현. 전 세션 인수인계 문서(2026-04-07-vworld-handoff.md §3) 참조.

---

## 아키텍처 메모

```
공시지가 조회 경로 (PR #196 이후 두 가지 병렬):
  1) WMS GetFeatureInfo → jiga/gosi_year 파싱 (useWmsClick.js)
  2) WMS에 데이터 없을 때 → 백엔드 /realestate/land-value?pnu= (MapView.jsx fallback)
     └ PR #195에서 domain 파라미터 추가로 복구됨

API 인증 구조:
  GitHub Secret: API_SECRET_KEY  → 백엔드 컨테이너 env
  GitHub Secret: VITE_API_KEY    → SWA 빌드 시 VITE_API_KEY로 주입
  ※ 두 값 동일해야 하며, 갱신 시 프론트엔드 재빌드 필수
  ※ 로컬 .env 키는 현재 구 키 (서버와 불일치 상태)
```

---

## ✅ 복구 완료 (2026-04-07 당일 세션)

| 작업 | 결과 |
| --- | --- |
| `az containerapp update` 로 Azure `API_SECRET_KEY` 복원, `VWORLD_DOMAIN` 분리 등록 | ✅ HTTP 200 확인 |
| `deploy-backend.yml:64` 따옴표 오기입 수정 | ✅ 커밋 완료 |
| GitHub Secrets `API_SECRET_KEY`, `VITE_API_KEY` 동일 값으로 동기화 | ✅ 완료 |
| SWA 재빌드 트리거 (PARK→main PR) | ✅ PR 생성 |
| `.github/workflows/smoke-test.yml` 추가 — 이후 배포마다 자동 인증 검증 | ✅ 커밋 완료 |
