# PR #73 (WOO → main) 진단 및 조치 지시

작성일: 2026-04-01
작성자: 진단 자동화 (Claude Code)

---

## 1. 진단 요약

### 왜 300개 이상의 커밋이 표시되는가?

WOO 브랜치는 **`git merge origin/main`을 반복해서 수행**하였으나, 그 과정에서 생성된 머지 커밋들이 GitHub PR 커밋 카운터에 전부 포함된다. WOO가 main을 향해 PR을 열면, GitHub은 "WOO의 전체 히스토리에 있는 커밋 중 main에서 직접 도달할 수 없는 것"을 나열하는데, 이 중 대부분이 과거 main의 커밋이 WOO의 머지 트리에 들어온 것들이다.

**실제 TerryBlackhoodWoo가 직접 작성한 고유 커밋 (PR #44 이후)**:

| 해시 | 날짜 | 내용 |
|------|------|------|
| `6cc13d8` | 2026-04-01 | 공식 프론트엔드 통합 완료(260401) |
| `099ebae` | 2026-04-01 | 프론트엔드 및 백엔드 연결 완료(260401) |
| `b8116e4` `d83738d` `7ebd368` `12275d0` | 2026-04-01 | .gitignore 재설정 및 cache 폴더 제외 |
| `a60752b` | 2026-03-31 | TERRY 작업 내용 저장 (SDOT 센서 및 데이터로더) |
| `cb21f42` `c3e5304` | 2026-03-30 | SOHOBI 지도 업데이트(260330) |
| `76cd3bc` | 2026-03-30 | 지도 랜드마크 보강 완료(260330) |
| `3787166` | 2026-03-27 | 지도 업데이트(260327) |

---

## 2. WOO가 실제로 기여하려는 파일 목록

`git diff main..origin/WOO --name-only` 기준으로, main에 없는 파일 변경사항:

### (A) 핵심 기여 — frontend 지도 컴포넌트 재구조화 (유효)

```
frontend/src/components/map/MapView.jsx
frontend/src/components/map/MapView.css
frontend/src/components/map/controls/DongTooltip.jsx
frontend/src/components/map/controls/MapControls.jsx
frontend/src/components/map/panel/CategoryPanel.jsx
frontend/src/components/map/panel/DongPanel.jsx
frontend/src/components/map/panel/DongPanel/BarRow.jsx
frontend/src/components/map/panel/DongPanel/GenderDonut.jsx
frontend/src/components/map/panel/DongPanel/RealEstatePanel.jsx
frontend/src/components/map/panel/DongPanel/SalesDetail.jsx
frontend/src/components/map/panel/DongPanel/SalesSummary.jsx
frontend/src/components/map/panel/DongPanel/StorePanel.jsx
frontend/src/components/map/panel/DongPanel/SvcPanel.jsx
frontend/src/components/map/panel/DongPanel/constants.js
frontend/src/components/map/panel/DongPanel/formatHelpers.js
frontend/src/components/map/panel/Layerpanel.jsx
frontend/src/components/map/panel/PopulationPanel.jsx
frontend/src/components/map/panel/RoadviewPanel.jsx
frontend/src/components/map/popup/LandmarkPopup.jsx
frontend/src/components/map/popup/StorePopup.jsx
frontend/src/components/map/popup/WmsPopup.jsx
frontend/src/hooks/map/useDongLayer.js
frontend/src/hooks/map/useLandmarkLayer.js
frontend/src/hooks/map/useMap.js
frontend/src/hooks/map/useMarkers.js
frontend/src/hooks/map/usePopulationLayer.js
frontend/src/hooks/map/useRealEstate.js
frontend/src/hooks/map/useWmsClick.js
```

> 이것이 PR의 실질적인 목적이다. 기존 flat 구조에서 `map/` 서브디렉토리로 재구조화된 지도 컴포넌트들.

### (B) TERRY 개인 폴더 업데이트 (병합 무관)

```
TERRY/p01_backEnd/DAO/landmarkDAO.py
TERRY/p01_backEnd/DAO/mapInfoDAO.py
TERRY/p01_backEnd/DAO/molitRtmsDAO.py
TERRY/p01_backEnd/DAO/populationDAO.py
TERRY/p01_backEnd/DAO/seoulRtmsDAO.py
TERRY/p01_backEnd/mapController.py
TERRY/p01_backEnd/realEstateController.py
TERRY/p02_frontEnd_React/src/MapApp.jsx
TERRY/p02_frontEnd_React/src/components/... (다수)
TERRY/p04_DataLoader/csv/sdot_sensor/... (SDOT 센서 CSV)
TERRY/ADM_LAW_CD_MAP.md
TERRY/README_SOHOBI_MAP.md
```

> TERRY/ 폴더는 개인 작업 폴더이므로 충돌 없이 그대로 머지 가능.

### (C) ⚠️ 문제 영역 — integrated_PARK/ 백엔드 파일 (스테일)

WOO 브랜치의 `integrated_PARK/` 파일들은 **2026-03-25 이후 main에 반영된 수십 건의 수정이 누락된 구버전**이다. 이 파일들을 그대로 머지하면 기존 배포 백엔드가 퇴행(regression)된다.

```
integrated_PARK/agents/admin_agent.py         ← main 버전 유지 필요
integrated_PARK/agents/chat_agent.py          ← main 버전 유지 필요
integrated_PARK/agents/finance_agent.py       ← main 버전 유지 필요
integrated_PARK/api_server.py                 ← main 버전 유지 필요
integrated_PARK/domain_router.py              ← main 버전 유지 필요
integrated_PARK/kernel_setup.py               ← main 버전 유지 필요
integrated_PARK/log_formatter.py              ← main 버전 유지 필요
integrated_PARK/logger.py                     ← main 버전 유지 필요
integrated_PARK/orchestrator.py               ← main 버전 유지 필요
integrated_PARK/plugins/admin_procedure_plugin.py
integrated_PARK/plugins/finance_simulation_plugin.py
integrated_PARK/prompts/signoff_admin/evaluate/skprompt.txt
integrated_PARK/prompts/signoff_finance/evaluate/skprompt.txt
integrated_PARK/session_store.py
integrated_PARK/signoff/signoff_agent.py
integrated_PARK/data/admin_procedures.json
```

---

## 3. TerryBlackhoodWoo에게 전달할 조치 지시

> **현재 상황**: WOO 브랜치가 main보다 최소 7일 이상 뒤처진 상태에서 PR이 열렸다. `integrated_PARK/`의 변경사항은 WOO의 기여 범위가 아니므로, 이 파일들은 main 버전으로 유지해야 한다.

### 방법 A — WOO 브랜치에서 rebase (권장)

```bash
# 1. WOO 브랜치로 이동
git checkout WOO

# 2. main 최신 상태로 merge
git fetch origin
git merge origin/main

# 3. 충돌 발생 시: integrated_PARK/ 는 main 버전 채택
#    (충돌 파일마다 아래 명령 실행)
git checkout --theirs integrated_PARK/agents/admin_agent.py
git checkout --theirs integrated_PARK/agents/chat_agent.py
git checkout --theirs integrated_PARK/agents/finance_agent.py
git checkout --theirs integrated_PARK/api_server.py
git checkout --theirs integrated_PARK/domain_router.py
git checkout --theirs integrated_PARK/kernel_setup.py
git checkout --theirs integrated_PARK/log_formatter.py
git checkout --theirs integrated_PARK/logger.py
git checkout --theirs integrated_PARK/orchestrator.py
git checkout --theirs integrated_PARK/session_store.py
git checkout --theirs integrated_PARK/signoff/signoff_agent.py
# ... 나머지 integrated_PARK/ 파일들도 동일

# 4. frontend/src/components/map/ 과 TERRY/ 는 WOO 버전 유지
#    (충돌 발생 시)
git checkout --ours frontend/src/components/map/MapView.jsx
# ... 나머지 frontend/src/components/map/ 파일들 동일

# 5. 머지 완료 후 커밋
git add .
git commit -m "chore: main 최신화 후 integrated_PARK 충돌 해소 (main 버전 채택)"

# 6. push
git push origin WOO
```

### 방법 B — 새 브랜치에 cherry-pick (더 깔끔)

```bash
# 1. main에서 새 브랜치 생성
git checkout -b WOO-clean origin/main

# 2. WOO의 고유 커밋만 cherry-pick
git cherry-pick 6cc13d8   # 공식 프론트엔드 통합 완료
git cherry-pick 099ebae   # 프론트엔드 및 백엔드 연결 완료
git cherry-pick a60752b   # TERRY 작업 내용 저장
git cherry-pick cb21f42   # 지도 업데이트 (3/30)
git cherry-pick 76cd3bc   # 랜드마크 보강
git cherry-pick d83738d   # gitignore 재설정

# 3. cherry-pick 중 integrated_PARK/ 파일에 충돌 발생 시 main 버전 유지
git checkout HEAD -- integrated_PARK/

# 4. push 후 기존 PR #73의 base 브랜치를 WOO-clean으로 변경 (또는 새 PR 생성)
git push origin WOO-clean
```

---

## 4. 검증 기준

PR 머지 전 다음을 확인:

- [ ] `git diff main...WOO --name-only | grep integrated_PARK` — 백엔드 파일 diff가 없어야 함 (또는 의도적 신규 변경만 남아야 함)
- [ ] `frontend/src/components/map/` 구조가 올바르게 들어왔는지 로컬에서 `npm run dev` 후 `/map` 라우트 확인
- [ ] `git log --oneline main..WOO | wc -l` — 커밋 수가 소수(10개 이내)여야 정상
