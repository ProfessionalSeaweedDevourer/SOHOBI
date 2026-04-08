# Git 워크플로우 개정 지시서 (Claude Code 전달용)

작성일: 2026년 4월 8일 (KST)
적용 시점: **2026년 4월 11일 이후** (4월 10일 최종 발표 이후)
우선순위: 현 상태의 작동 가능한 제품 유지가 0순위. 발표 전에는 본 문서의 어떤 변경도 적용하지 말 것.

---

## 0. 발표 전(4월 10일까지) 임시 운영 규칙

- 본 문서의 워크플로우 변경은 **적용 금지**.
- `patch contents already upstream` 충돌이 발생하면 기존 브랜치를 수정하지 말고, 아래 우회 절차만 사용한다.

```bash
git fetch origin
git checkout -b PARK/hotfix-temp origin/main
git cherry-pick <필요한 커밋 해시들>
git push origin PARK/hotfix-temp
# PR 생성 → squash merge
```

- 워크플로우 전반 변경, CLAUDE.md 수정, 브랜치 삭제 등은 발표 종료 후 별도 지시에 따라 진행한다.

---

## 1. 배경 및 문제 정의

squash merge 전략에서 팀원 브랜치(PARK 등)를 장기 유지하면, main에 squash-merge된 커밋들이 브랜치 히스토리에 그대로 남는다. 다음 PR을 위해 `git rebase origin/main`을 실행하면 이미 main에 반영된 변경을 재적용하려다 `patch contents already upstream` 충돌이 반복된다.

추가로, 두 세션이 **같은 워킹 디렉토리**를 공유하면 한쪽의 `checkout`·`reset`이 다른 세션의 작업을 파괴할 수 있다. 이는 브랜치 전략만으로는 해결되지 않는 별도 문제다.

---

## 2. 채택 결정 사항

### 2.1 브랜치 모델: main 기반 단명 브랜치

- 모든 작업은 매번 `origin/main`에서 분기한 단명 브랜치에서 진행한다.
- 팀원 기준 브랜치(PARK, NAM, WOO, JANG, CHOI 등)는 **git 브랜치로 보존하지 않는다.** 명명 컨벤션의 일부로만 존재한다.
- 명명 규칙은 업계 표준 타입 prefix를 따른다.

```
feat/park-<작업명>
fix/park-<작업명>
chore/park-<작업명>
docs/park-<작업명>
refactor/park-<작업명>
```

타입은 Conventional Commits 규약을 따른다(`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`).

### 2.2 세션 격리: git worktree 도입

같은 저장소에 대해 동시에 두 개 이상의 세션을 운영할 경우, 반드시 `git worktree`로 디렉토리를 분리한다.

```bash
# 메인 저장소: ~/dev/sohobi
# 추가 세션용 worktree
git worktree add ../sohobi-feat-refresh -b feat/park-refresh-button origin/main
git worktree add ../sohobi-fix-auth -b fix/park-auth-token origin/main
```

worktree 정리:

```bash
git worktree list
git worktree remove ../sohobi-feat-refresh
```

### 2.3 rebase 정책 완화

- squash merge 전제에서는 PR 브랜치 내부 히스토리가 어차피 버려지므로 rebase를 강제하지 않는다.
- main이 앞서가 있고 충돌이 없으면 GitHub의 "Update branch" 버튼(merge from main) 사용을 허용한다.
- 충돌이 있을 때만 로컬 rebase 또는 merge로 해결한다.

### 2.4 미커밋 변경 보호: WIP 커밋 권장

`git stash` 대신 WIP 커밋을 권장한다. reflog에 영구 기록되어 사고 복구가 쉽다.

```bash
git add -A
git commit -m "WIP: <작업명>" --no-verify
```

PR 생성 전에 `git reset --soft HEAD~1` 또는 `git rebase -i`로 정리한다.

### 2.5 GitHub 저장소 설정 (관리자 작업)

다음을 활성화한다.

- **PR 머지 방식: Squash and merge만 허용** (Merge commit, Rebase merge 비활성화)
- **Automatically delete head branches: 활성화**
- **main 브랜치 보호 규칙**:
  - 직접 push 금지
  - PR 필수
  - 리뷰 1인 이상 승인 필수
  - 머지 전 브랜치가 main과 동기화되어 있어야 함(선택)

---

## 3. CLAUDE.md 개정 지시

### 3.1 "PR / 커밋 규칙" 섹션 — 브랜치 테이블

**삭제할 내용:** 팀원별 고정 브랜치 테이블 ("작업 브랜치는 아래 팀원별 브랜치 사용" 부분 전체).

**대체할 내용:**

```markdown
## 브랜치 명명 규칙

모든 작업 브랜치는 `origin/main`에서 신규 분기하여 단명 브랜치로 운영한다.
팀원 기준 브랜치(PARK, NAM 등)는 git 브랜치로 존재하지 않으며, 명명 컨벤션의 일부로만 사용한다.

형식: `<type>/<author>-<작업명>`

- type: feat, fix, chore, docs, refactor, test, perf, build, ci
- author: park, nam, woo, jang, choi
- 작업명: kebab-case, 영문 소문자

예시:
- feat/park-signoff-agent
- fix/nam-gov-api-timeout
- refactor/woo-map-loader
- chore/choi-rag-index-rebuild
```

### 3.2 "Rebase 기반 워크플로우" 섹션

**삭제할 내용:** 기존 rebase + `--skip` 절차 전체.

**대체할 내용:**

```markdown
## 작업 절차

1. main 최신화 및 브랜치 생성
   ```bash
   git fetch origin
   git checkout -b feat/park-<작업명> origin/main
   ```

2. 작업 및 커밋

3. 원격 푸시
   ```bash
   git push origin feat/park-<작업명>
   ```

4. main이 앞서갔을 경우
   - 충돌이 없으면: GitHub PR 화면의 "Update branch" 사용
   - 충돌이 있으면: 로컬에서 `git rebase origin/main` 후 `git push --force-with-lease`

5. PR 생성 → 리뷰 → Squash and merge

6. 머지 후 브랜치는 GitHub 설정에 의해 자동 삭제됨. 로컬 브랜치는 수동 정리:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feat/park-<작업명>
   ```

## 동시 작업 시 (worktree)

같은 저장소에 대해 두 개 이상의 작업을 병행할 경우 반드시 worktree를 사용한다.

```bash
git worktree add ../sohobi-<작업명> -b feat/park-<작업명> origin/main
cd ../sohobi-<작업명>
# 작업
```

작업 종료 후:
```bash
git worktree remove ../sohobi-<작업명>
```

## 미커밋 변경 보호

긴 작업 중간 저장은 stash 대신 WIP 커밋을 사용한다.

```bash
git add -A && git commit -m "WIP: <작업명>" --no-verify
```

PR 생성 전 `git reset --soft HEAD~1` 또는 `git rebase -i`로 정리한다.
```

---

## 4. 도입 절차 (발표 후)

1. **4월 11일 오전**: 본 문서를 팀에 공유하고 5분 간 합의 확인
2. **4월 11일**: 관리자가 GitHub 저장소 설정 변경 (3개 항목)
3. **4월 11일**: CLAUDE.md 개정 PR 생성 및 머지
4. **4월 11일**: 기존 팀원 브랜치를 archive tag로 보존한 후 원격에서 삭제
   ```bash
   git fetch origin
   for b in PARK NAM WOO JANG CHOI; do
     git tag "archive/$b-2026-04-11" "origin/$b"
     git push origin "archive/$b-2026-04-11"
   done
   git push origin --delete PARK NAM WOO JANG CHOI
   ```
   - archive tag는 최소 1주일(4월 18일 회고일까지) 보존
   - 회고 후 문제 없으면 다음 명령으로 정리:
     ```bash
     for b in PARK NAM WOO JANG CHOI; do
       git push origin --delete "archive/$b-2026-04-11"
     done
     ```
5. **4월 11~17일**: 신규 워크플로우로 작업 진행, 충돌 발생 사례 기록
6. **4월 18일**: 1주일 회고. 충돌 발생률·체감 마찰 평가. 문제 없으면 archive tag 정리.

---

## 5. 롤백 기준

다음 중 하나라도 해당되면 본 워크플로우를 원복하고 재논의한다.

- 도입 1주일 내 머지 사고 1건 이상 발생
- 팀원 5인 중 2인 이상이 명명 규칙·worktree 사용에 명확한 마찰을 호소
- 충돌 발생률이 기존 대비 개선되지 않음

---

## 6. 검증 절차 (도입 직후)

1. 새 브랜치 `chore/park-test-workflow`를 `origin/main` 기반으로 생성
2. 더미 커밋 추가 후 PR 생성
3. Squash merge 후 동일 명명 패턴의 신규 브랜치를 다시 main 기반으로 생성하여 충돌 없이 작업 가능한지 확인
4. 두 개의 worktree에서 각각 `feat/park-session1`, `feat/park-session2` 브랜치 작업 → 디렉토리·인덱스 간섭 없음 확인

---

## 7. 작업 파일

- `CLAUDE.md` — 3.1, 3.2 항목 반영
- GitHub 저장소 설정 — 2.5 항목 반영 (관리자: 에릭 직접 작업)
- 기존 팀원 브랜치 archive tag 보존 후 삭제 — 도입 절차 4번 (1주일 후 회고 시 정리)
