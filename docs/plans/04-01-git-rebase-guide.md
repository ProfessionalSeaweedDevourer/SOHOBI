# PR 올리기 전에 꼭 읽어주세요 — 브랜치 관리 가이드

작성일: 2026-04-01

---

## 이 문서를 쓰는 이유

PR을 열었을 때 커밋이 300개 이상으로 표시되는 문제가 있었습니다.
실제로 새로 작업한 내용은 몇 개뿐인데도요.
이 문서는 그 원인과 올바른 해결 방법을 처음 보는 사람도 이해할 수 있도록 설명합니다.

---

## 먼저 알아야 할 개념들

### 브랜치(Branch)란?

코드를 수정할 때, 공용 코드를 직접 건드리지 않고 **나만의 복사본**을 만들어서 작업하는 공간입니다.

예를 들어 팀 전체가 쓰는 공용 코드가 `main` 브랜치에 있고, 나는 `WOO`라는 내 브랜치를 만들어서 거기서 작업합니다.

```
main 브랜치:  공용 코드 (팀 전체가 사용)
WOO 브랜치:   내 작업 공간 (main을 복사해서 시작)
```

### 커밋(Commit)이란?

내가 파일을 수정하고 "저장했다"고 기록하는 단위입니다. 작업 일지의 한 줄이라고 생각하면 됩니다.

```
커밋 A: 지도 백엔드 추가
커밋 B: 지도 프론트 연결
커밋 C: 버그 수정
```

### PR(Pull Request)이란?

내 브랜치에서 작업한 내용을 공용 `main` 브랜치에 반영해달라고 요청하는 것입니다.
PR을 열면 팀원들이 내 변경사항을 검토(리뷰)한 뒤 승인하면 합쳐집니다.

---

## 문제가 생기는 상황

내가 `WOO` 브랜치에서 작업하는 동안, 다른 팀원들도 계속 `main`에 코드를 추가합니다.
시간이 지날수록 `main`과 내 브랜치 사이의 거리가 벌어집니다.

```
처음:
main: ──A──B──C
                \
WOO:             D──E  (내 작업)

한 달 후:
main: ──A──B──C──────────────────────Z  (팀원들이 계속 추가)
                \
WOO:             D──E  (나는 여기서 멈춰있음)
```

이 상태에서 PR을 열면, GitHub은 WOO와 main 사이의 **모든 차이**를 커밋으로 표시합니다.
실제로 내가 작성한 커밋은 D, E 두 개뿐이지만, 그 사이에 쌓인 팀원 커밋들까지 모두 표시되어 수백 개처럼 보이는 것입니다.

---

## 잘못된 해결 방법: `git merge origin/main`

가장 흔히 저지르는 실수는 main의 변경을 내 브랜치로 가져올 때 `merge`를 쓰는 것입니다.

```bash
git merge origin/main   ← ❌ 이렇게 하면 안 됩니다
```

`merge`는 "두 브랜치를 합쳤다"는 **흔적 커밋(머지 커밋)**을 하나 더 만듭니다.
main을 한 번 가져올 때마다 이 흔적이 하나씩 쌓입니다.

```
WOO: D──E──M1──M2──M3──M4──M5 ...
           ↑   ↑   ↑   ↑   ↑
           main 가져올 때마다 생기는 흔적들
```

PR을 열면 이 흔적 커밋들이 전부 표시되어 커밋이 수백 개처럼 보입니다.
내가 실제로 작업한 것은 D, E 두 개뿐인데도요.

---

## 올바른 방법: `git rebase origin/main`

`rebase`는 흔적을 남기지 않고, 내 작업을 **main의 최신 상태 바로 뒤에 붙여놓습니다.**

```bash
git fetch origin         # main 최신 상태 가져오기
git rebase origin/main   # 내 작업을 main 끝에 붙이기
```

그림으로 보면 이렇습니다.

```
전:
main: ──A──B──C──F──G
                \
WOO:             D──E

후:
main: ──A──B──C──F──G
                      \
WOO:                   D──E  ← D, E가 G 뒤로 깔끔하게 이동
```

PR을 열면 D, E 두 개만 표시됩니다. 팀원들도 내가 뭘 만들었는지 한눈에 볼 수 있습니다.

---

## 충돌(Conflict)이 발생하면?

rebase 중에 "내가 수정한 파일을 팀원도 수정한 경우" 충돌이 발생할 수 있습니다.
이건 merge를 써도 똑같이 발생하므로, rebase 고유의 문제가 아닙니다.

```bash
# 충돌이 발생하면 터미널에 이런 메시지가 뜹니다:
# CONFLICT (content): Merge conflict in 파일명.py

# 1. 충돌난 파일을 VS Code에서 열어 수정합니다
#    (VS Code가 "Accept Current Change / Accept Incoming Change" 버튼을 보여줍니다)

# 2. 수정 완료 후
git add 파일명.py
git rebase --continue

# 중간에 그냥 취소하고 싶으면
git rebase --abort
```

---

## PR 올리기 전 2분 체크

PR을 열기 전에 아래 명령어를 한 번만 실행해 보세요.

```bash
git log --oneline origin/main..HEAD
```

이 명령어는 **"내가 작성한 커밋만"** 보여줍니다.
결과에 내가 쓴 커밋 메시지만 나오면 정상입니다.

```text
예시 (정상):
  a1b2c3d 지도 랜드마크 보강 완료
  e4f5g6h 프론트엔드 통합 완료

예시 (비정상 — rebase가 필요한 상태):
  a1b2c3d 지도 랜드마크 보강 완료
  e4f5g6h 프론트엔드 통합 완료
  x9y8z7w Merge branch 'main' of https://github.com/...  ← 이런 게 보이면 rebase 필요
  u6v5w4t Merge branch 'main' of https://github.com/...
  ...수십 개 이상
```

---

## 요약: 앞으로의 작업 순서

### 1. 작업 시작 전 (또는 2~3일마다)

```bash
git fetch origin
git rebase origin/main
```

### 2. PR 올리기 전

```bash
git log --oneline origin/main..HEAD
# → 내 커밋만 나오는지 확인
```

### 3. PR 올리기

```bash
git push origin 내브랜치명
# → GitHub에서 PR 생성
```

---

## 이미 merge를 많이 써버렸다면

지금 당장 정리하는 방법입니다.

```bash
# 1. main 최신 상태로 새 브랜치 만들기
git fetch origin
git checkout -b 내브랜치명-clean origin/main

# 2. 기존 브랜치에서 내가 직접 작성한 커밋 해시 찾기
git log --oneline --no-merges origin/main..내브랜치명

# 3. 그 커밋들만 새 브랜치에 가져오기
git cherry-pick 커밋해시1
git cherry-pick 커밋해시2

# 4. push
git push origin 내브랜치명-clean
```

이후 기존 PR은 닫고, 새 브랜치로 PR을 다시 엽니다.

---

> **한 줄 요약:**
> main의 내용을 가져올 때는 `git merge` 대신 `git rebase origin/main`을 쓰세요.
> merge를 쓰면 흔적이 쌓여 PR이 수백 개짜리처럼 보입니다.
