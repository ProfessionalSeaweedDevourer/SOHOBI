# 인수인계 문서 — 2026-04-07 (지도 지적도/공시지가 버그)

## 브랜치 / PR 상태

| 항목 | 내용 |
|------|------|
| 수정 포함 PR | [#191](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/191) — main 머지 완료 |
| 수정 커밋 메시지 | `fix: 지적도 레이어 초기화 복원 — mapReady 시점 생성 + 공시지가 에러 로깅` |
| 분석 근거 커밋 | `00e878f` (WOO-clean2, PR#177) — 로컬에서 정상 작동하던 원본 구현 |

---

## 버그 원인 및 수정 내용

### Bug 1 — 지적도 레이어 기본 ON인데 실제 미표시

**증상:** 앱 로드 후 줌 17+ 이동해도 지적도 미표시. 레이어 패널 열고 OFF→ON 토글해야 뒤늦게 나타남.

**원인 (이중):**

| 원인 | 파일 | 내용 |
|------|------|------|
| A (주요) | `MapView.jsx:88` | `showPanel = useState(false)` → Layerpanel 미마운트 → 레이어 초기화 useEffect 미실행 |
| B (부수) | `MapView.jsx:770` | PR#175 cherry-pick 시 Layerpanel에 `mapReady` prop 전달 누락, 의존성 `[map]`으로 축소 |

**수정:**
- `MapView.jsx` `useEffect([mapReady])` 블록에 지적도 레이어 동적 생성 코드 추가 (PR#177 의도 복원)
- Layerpanel에 `mapReady={mapReady}` prop 전달 추가
- `Layerpanel.jsx` init effect를 `[map, mapReady]` 의존성 + 500ms timeout으로 복원

**수정 파일:**
- `frontend/src/components/map/MapView.jsx` (lines ~139-171, ~797)
- `frontend/src/components/map/panel/Layerpanel.jsx` (lines ~58-100)

---

### Bug 2 — 공시지가 정보 항상 "없음"

**증상:** 지적도 클릭 시 팝업에 주소·PNU는 표시되나 공시지가 값이 항상 누락.

**현재 상태: 원인 미확정, 로깅 추가로 진단 준비 완료**

**공시지가 조회 흐름:**
```
지적도 클릭
  → WMS GetFeatureInfo → jiga/pblntfPclnd 필드 (LP_PA_CBND_BUBUN은 경계 레이어라 대부분 없음)
  → fallback: REALESTATE_URL/realestate/land-value?pnu=xxx
      → landValueDAO.py → api.vworld.kr/req/data (VWorld Data API)
      → 결과 없으면 data: [] → "공시지가 정보 없음"
```

**유력 원인 — VWorld Data API Azure IP 미등록:**
- VWorld API 키는 IP/도메인 기반 인증. `localhost`는 등록되어 있어 WOO 로컬에서 정상 동작
- Azure Container Apps 외부 IP가 VWorld 개발자 센터에 미등록이면 `api.vworld.kr/req/data` 호출이 403으로 실패
- 이전까지 `.catch(() => {})` 무음 처리로 실패가 은폐되어 있었음

**수정:** `.catch(() => {})` → `.catch((err) => console.error("[공시지가 조회 실패]", err))`

---

## 다음 세션 작업

### 공시지가 원인 확정 절차

1. **배포 후 브라우저 콘솔 확인:**
   - 지적도 레이어 클릭
   - 콘솔에서 `[공시지가 조회 실패]` 메시지 확인
   - 에러 타입에 따라 분기:

   | 에러 | 원인 | 조치 |
   |------|------|------|
   | `Failed to fetch` / CORS | Azure → VWorld 네트워크 차단 | VWorld 개발자 센터에서 Azure IP 등록 |
   | 응답 `status: "ERROR"` | API 키 미인증 | 동일 (IP 등록) |
   | 에러 없음 + `data: []` | 해당 필지 데이터 미존재 | 정상 케이스, 표시 문구 유지 |

2. **Azure Container Apps IP 확인:**
   ```bash
   # Azure Portal 또는 CLI에서 outbound IP 확인
   az containerapp show -n sohobi-backend -g <resource-group> --query "properties.outboundIpAddresses"
   ```

3. **VWorld 개발자 센터:** [https://www.vworld.kr/dev/v4dv_apikey_s002.do](https://www.vworld.kr/dev/v4dv_apikey_s002.do)
   - API 키 `<VWORLD_API_KEY>` → IP 허용 목록에 Azure outbound IP 추가

---

## 관련 파일 참조

| 파일 | 역할 |
|------|------|
| `frontend/src/components/map/MapView.jsx` | 지적도 레이어 초기화 (`useEffect([mapReady])`) + 공시지가 fallback fetch |
| `frontend/src/components/map/panel/Layerpanel.jsx` | 레이어 ref 연결, toggleCadastral |
| `frontend/src/hooks/map/useWmsClick.js` | WMS 클릭 처리, `parseWmsProps` (jiga 필드 파싱) |
| `integrated_PARK/db/dao/landValueDAO.py` | VWorld Data API 호출 (공시지가 이력 5년) |
| `integrated_PARK/realestate_router.py` | `/realestate/land-value` 엔드포인트 |
