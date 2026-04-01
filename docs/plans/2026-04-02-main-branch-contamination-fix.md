# main 브랜치 오염 진단 및 복구 플랜

## Context
WOO(TerryBlackhoodWoo)가 PR 없이 WOO-clean2 브랜치를 origin/main에 직접 force push함.
결과적으로 현재 origin/main의 HEAD commit 메시지가 **"Merge branch 'main'... into WOO-clean2"** —
즉 자기 브랜치로 역방향 merge한 commit이 main의 선단이 된 상태.

---

## 진단: 무슨 일이 일어났나

### WOO의 작업 순서 (재구성)
```
WOO-clean2 브랜치에서:
  ca40810  공식 프론트엔드 통합 완료(260401)   ← 30 files, 대규모 map 컴포넌트 리팩터
  0f91fc6  프론트엔드 및 백엔드 연결 완료(260401)
  541c967  chore: 리베이스 전 임시 저장         ← ⚠️ WIP commit ("하려다가 그냥 push")
  00593a4  feat: WOO 브랜치 작업물 최종 이관 및 main 동기화
  e8c848d  맵 UI개선(260401)-중간 저장          ← ⚠️ WIP commit
  6712459  맵 UI 개선_쿨로스터 체크방식 변경(260401)
  dd87c4a  Merge branch 'main'... into WOO-clean2  ← git pull origin main 한 결과

→ 이 상태를 git push origin HEAD:main (또는 WOO-clean2:main) 으로 직접 push
```

### origin/main 현재 상태
- HEAD: `dd87c4a` — "Merge branch 'main'... **into WOO-clean2**" (역방향 merge commit)
- 직전 정상 HEAD: `1efac39` — "Merge pull request #80 from .../NAM" (2026-04-01 PR 정상 머지)

### 피해 범위

| 영역 | 상태 | 설명 |
|------|------|------|
| `integrated_PARK/` (백엔드) | **정상** | dd87c4a의 backend 변경분은 PR #78·#79·#80에서 정식 머지된 것. WOO 커밋들은 backend 건드리지 않음 |
| `frontend/src/components/map/` | **미검증** | WOO가 단독으로 수정. MapView.jsx 500줄+ diff, WIP 커밋 포함, PR 리뷰 없음 |
| `frontend/vite.config.js` | **변경됨** | 새 proxy 경로 다수 추가 (`/map/nearby`, `/map/landmarks` 등 TERRY 서버용) |
| `TERRY/` 개인 폴더 | **무관** | main에 들어왔지만 실행 경로 아님 |
| git 히스토리 | **오염** | WIP 커밋 2개 + 역방향 merge commit이 main history에 영구 기록 |

---

## 리스크 평가

### 즉각적인 구동 위험
- **백엔드(`integrated_PARK/`)**: 없음. WOO 커밋이 backend를 건드리지 않았고, PR #80 변경분(domain_router, gov_support_plugin)은 정상 검증된 코드.
- **프론트엔드**: 실행 전까지 확인 불가. WIP 커밋 포함이라 `npm run dev` 시 빌드 오류 가능성 존재.
  - 특히 `541c967`에서 `PopulationPanel.jsx`, `RoadviewPanel.jsx` 삭제 후 `00593a4`에서 재추가하는 add→delete→add 패턴 확인됨.

### 중장기 위험
- WOO 작업 방식이 교정되지 않으면 같은 패턴 반복
- 다른 팀원들이 이 오염된 main을 기준으로 rebase하면 WIP 커밋이 각자 히스토리에 전파됨

---

## 복구 계획

### 목표 상태
```
origin/main → 1efac39 (Merge PR #80, 정상 상태)
origin/WOO-clean2 → dd87c4a (WOO 작업 보존, PR 대기)
```

### Step 1: origin/main을 1efac39로 force reset
```bash
git push origin 1efac39:refs/heads/main --force
```
- `1efac39`는 PR #80(NAM)이 정상 머지된 마지막 검증 시점
- WOO 커밋 6개 + 역방향 merge commit이 main에서 제거됨
- WOO-clean2 브랜치는 dd87c4a 그대로 유지되므로 작업 손실 없음

### Step 2: WOO에게 WIP 커밋 정리 후 PR 제출 요청

WOO가 해야 할 작업:
```bash
git checkout WOO-clean2
git rebase -i 1efac39  # 6개 커밋 squash/fixup, WIP 커밋 제거
git push origin WOO-clean2 --force-with-lease
# GitHub에서 WOO-clean2 → main PR 생성
```
- 반드시 "리베이스 전 임시 저장", "중간 저장" 커밋은 squash 처리
- PR 본문에 변경사항 요약 + 스크린샷 필요

### Step 3: PR 리뷰 항목 (담당자 확인 필요)
- [ ] `npm run dev` 후 map 기능 정상 동작 확인
- [ ] vite.config.js의 TERRY 전용 proxy(8681, 8682 포트) — 팀 공용 설정으로 적절한지 확인
- [ ] `MapView.jsx`, `StorePopup.jsx` 대규모 변경분 코드 리뷰

---

## 검증
```bash
# 복구 후 확인
git fetch origin
git log --oneline origin/main | head -5
# → 1efac39 Merge pull request #80 from .../NAM 가 HEAD여야 함

# WOO 작업 보존 확인
git log --oneline origin/WOO-clean2 | head -3
# → dd87c4a가 아직 있어야 함
```
