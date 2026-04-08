# squash-merge 재충돌 문제 — 구조적 개선 플랜

## Context

squash merge 전략에서 팀 브랜치(PARK 등)를 장기 유지하면, 이미 main에 squash-merge된 커밋들이 브랜치 히스토리에 그대로 남는다. 다음 PR을 위해 `git rebase origin/main`을 실행하면 이 커밋들을 재적용하려다 충돌(`patch contents already upstream`)이 반복된다. 제안된 해결책("PR 머지 후 팀 브랜치를 `git reset --hard origin/main`으로 리셋")이 멀티 세션 환경에서 안전한지 검토 요청.

---

## 위험 분석

### git stash만으로 충분한가? → **아니오**

`git stash`는 **현재 세션의 워킹 트리만** 보호한다.

| 시나리오 | 결과 |
|----------|------|
| Session A가 stash 후 `reset --hard` → Session A의 unstashed 변경은 보호됨 | ✅ 안전 |
| Session B가 같은 디렉토리에서 작업 중인데 Session A가 `reset --hard` 실행 | ❌ **Session B의 미커밋 변경 파괴** |
| Session B가 이미 push했는데 Session A가 `push --force-with-lease` 실행 | ⚠️ force-with-lease가 막아줌 (fetch 시점 이후 push가 없었다면) |

**핵심**: 두 세션이 **같은 디렉토리**를 공유하면 `reset --hard`는 세션 구분 없이 워킹 트리 전체를 덮어쓴다. stash는 다른 세션을 보호하지 못한다.

### `--force-with-lease`의 한계

원격 보호만 한다. 로컬 미커밋 변경 보호 기능 없음.

---

## 해결안 비교

### ❌ 안 쓸 것: PR 머지 후 팀 브랜치 hard reset

```bash
git reset --hard origin/main && git push --force-with-lease
```

멀티 세션 환경에서 다른 세션의 미커밋 작업을 파괴할 수 있어 채택하지 않는다.

---

### ✅ 채택안: PR마다 main 기반 fresh 브랜치 사용

팀 브랜치(PARK)는 **기준점(base ref)** 으로만 유지하고, 실제 작업은 매번 main에서 분기한 단명 브랜치에서 진행한다.

```bash
# PR 시작 시
git fetch origin
git checkout -b PARK-fix-refresh-button origin/main

# 작업 → 커밋

# PR 전 rebase (이미 main 기반이므로 --skip 없음)
git rebase origin/main
git push origin PARK-fix-refresh-button

# PR: PARK-fix-refresh-button → main
```

**효과:**
- rebase 시 `patch already upstream` 충돌 완전 소멸 (브랜치가 항상 최신 main에서 출발)
- 세션 간 간섭 없음 (각 세션이 독립 브랜치 사용)
- 팀 브랜치(PARK)는 건드리지 않으므로 영구 보존 규칙 유지

**단점:**

- 브랜치 명명 규칙 추가 필요 (`PARK-작업명` 패턴 — 슬래시 불가)
- CLAUDE.md의 "작업 브랜치는 팀원 브랜치 사용" 규칙 개정 필요

> **git ref 제약**: `PARK` 브랜치가 존재하면 `PARK/작업명`(슬래시) 패턴으로 브랜치 생성 불가.  
> git은 refs를 파일시스템 경로로 저장하므로 `PARK`(파일)와 `PARK/`(디렉토리)가 공존할 수 없다.  
> 반드시 **대시(`PARK-작업명`)** 패턴을 사용한다.

---

## CLAUDE.md 변경 사항

### 변경할 섹션: "PR / 커밋 규칙" 내 브랜치 테이블

**현행:**
> 작업 브랜치는 아래 팀원별 브랜치 사용

**개정안:**
> 작업 브랜치는 `팀원브랜치/작업명` 패턴으로 main에서 신규 생성.  
> 팀원 브랜치(PARK 등)는 네임스페이스 prefix 용도로만 유지하며 직접 커밋하지 않는다.

### 변경할 섹션: "Rebase 기반 워크플로우"

**현행 절차 (rebase + 충돌 시 --skip):**
전체 삭제.

**개정안 절차:**
```bash
# 1. main 기반 브랜치 생성
git fetch origin
git checkout -b PARK-<작업명> origin/main

# 2. 작업 및 커밋

# 3. PR 직전 rebase (충돌 없음)
git rebase origin/main
git push origin PARK-<작업명>

# 4. PR 생성 후 머지
# 5. 브랜치 삭제 여부: PARK-<작업명>은 단명 브랜치이므로 머지 후 삭제 가능
#    (팀원 기준 브랜치 PARK 자체는 유지)
```

---

## 검증 방법

1. 새 브랜치 `PARK/test-workflow`를 `origin/main` 기반으로 생성
2. 더미 커밋 추가 후 PR 생성
3. squash merge 후 동일 브랜치에서 `git rebase origin/main` 재실행 → `--skip` 없이 완료되는지 확인
4. 병행 세션 시뮬레이션: 두 터미널에서 각기 `PARK-session1`, `PARK-session2` 브랜치로 작업 → 간섭 없음 확인

---

## 작업 파일

- `CLAUDE.md` — "PR / 커밋 규칙" 브랜치 테이블 + "Rebase 기반 워크플로우" 섹션 개정
