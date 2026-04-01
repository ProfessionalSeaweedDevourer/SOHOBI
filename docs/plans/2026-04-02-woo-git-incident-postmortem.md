# Git 사고 리포트 — WOO 브랜치 직접 push 사건

> 작성일: 2026-04-02  
> 대상: TerryBlackhoodWoo  
> 사건 커밋: `ca40810` ~ `dd87c4a` (origin/main 직접 push)

---

## 먼저 — 이 문서를 읽는 이유

이번에 작업하면서 의도치 않게 `main` 브랜치를 오염시켰습니다.  
코드 자체는 다행히 동작하지만, **git 히스토리에 돌이킬 수 없는 흔적이 남았습니다.**

이게 왜 문제인지, 무슨 일이 일어났는지, 앞으로 어떻게 해야 하는지를 이 문서에서 설명합니다.  
어렵지 않습니다. 끝까지 읽어주세요.

---

## 1. 무슨 일이 일어났나

### 실제로 일어난 순서

```
[WOO-clean2 브랜치에서 작업]

  커밋 1: 공식 프론트엔드 통합 완료(260401)
  커밋 2: 프론트엔드 및 백엔드 연결 완료(260401)
  커밋 3: chore: 리베이스 전 임시 저장       ← ⚠️
  커밋 4: WOO 브랜치 작업물 최종 이관 및 main 동기화
  커밋 5: 맵 UI개선(260401)-중간 저장         ← ⚠️
  커밋 6: 맵 UI 개선_쿨로스터 체크방식 변경

  [git pull origin main 실행]
  커밋 7: Merge branch 'main' ... into WOO-clean2   ← ⚠️⚠️

[이 상태 그대로 origin/main에 직접 push]
```

### 결과

현재 `origin/main`의 가장 최신 커밋 메시지:

```
Merge branch 'main' of https://github.com/.../SOHOBI into WOO-clean2
```

**main 브랜치의 최신 커밋이 "WOO-clean2에 병합" 이라고 쓰여 있습니다.**  
이건 히스토리를 보는 모든 사람에게 혼란을 줍니다.

---

## 2. 역방향 Merge란 무엇인가

### 정방향 Merge (올바른 방향)

```
main ──────●──────────────────●──── (계속)
            \                /
             ●──●──●──●──●──    ← 내 브랜치에서 작업 후 PR로 main에 합치기
```

- 내 브랜치에서 작업
- PR 제출
- main에 병합 (merge)

### 역방향 Merge (이번 사건)

```
main ──────●──────────────────●
            \                  \
             ●──●──●──●──●──────●──→ main에 직접 push
                              ↑
                      "main을 내 브랜치로 당겨온" merge commit
```

`git pull origin main`을 실행하면 **main을 내 브랜치로 당겨옵니다.**  
이건 정상적인 행동이지만, **그 결과를 main에 직접 push하면** 안 됩니다.

직접 push한 순간, "내 브랜치에 main을 합쳤습니다"라는 기록이 main 자체에 새겨집니다.  
마치 "나는 오늘 나 자신에게 편지를 보냈다"처럼 이상한 기록입니다.

---

## 3. 왜 있어서는 안 되는 일인가

### 3-1. WIP(미완성) 커밋이 main에 들어왔습니다

이번에 main에 들어온 커밋 이름을 보십시오:

| 커밋 | 메시지 | 문제 |
|------|--------|------|
| `541c967` | **리베이스 전 임시 저장** | "일단 저장해두자"는 개인 메모가 main에 영구 기록 |
| `e8c848d` | **맵 UI개선-중간 저장** | 작업 도중의 불안정한 상태가 main에 영구 기록 |

`git log`는 영구 기록입니다. 이 커밋들은 1년 뒤에도 `main` 히스토리에 남아 있습니다.

> 비유하자면: 회사 공식 문서 보관함에 "나중에 다시 써야 함 (임시)" 라고 적힌 초안을 집어넣은 것입니다.

### 3-2. 코드 리뷰가 없었습니다

PR을 거치면:
- 다른 팀원이 코드를 검토합니다
- 문제가 있으면 머지 전에 발견됩니다
- 변경사항이 문서화됩니다

이번에는 30개 이상의 파일 변경이 아무 검토 없이 main에 들어갔습니다.  
다행히 빌드는 됐지만, 논리 오류나 버그가 있었다면 팀 전체가 영향을 받을 수 있었습니다.

### 3-3. 다른 팀원의 작업을 방해할 수 있습니다

다른 팀원들은 `main`을 기준으로 자신의 브랜치를 최신화합니다.  
main이 오염되면, 그 오염이 모든 팀원의 브랜치로 전파됩니다.

---

## 4. 올바른 작업 흐름

### 기본 흐름 (항상 이 순서)

```bash
# 1. main 최신화 (내 로컬 main을 업데이트)
git checkout main
git pull origin main

# 2. 내 브랜치로 이동
git checkout WOO-clean2

# 3. main의 최신 내용을 내 브랜치에 적용 (rebase)
git rebase origin/main
#    ↑ pull이 아닙니다! rebase입니다!

# 4. 작업, 커밋

# 5. push (내 브랜치로만)
git push origin WOO-clean2 --force-with-lease

# 6. GitHub에서 PR 생성: WOO-clean2 → main
```

### pull vs rebase — 차이점

| | `git pull origin main` | `git rebase origin/main` |
|---|---|---|
| 무슨 일이 일어나나 | main을 내 브랜치로 **당겨와서 merge** | 내 커밋들을 main 위에 **재배치** |
| merge commit 생성 | **생긴다** ("Merge branch 'main' into ...") | **생기지 않는다** |
| 히스토리 모양 | 복잡하게 얽힘 | 깔끔한 직선 |
| 권장 여부 | ❌ (브랜치 작업 중에는 사용 금지) | ✅ |

> rebase 상세 가이드는 `docs/plans/2026-04-01-git-rebase-guide.md` 참고

### PR 전 커밋 정리 (필수)

```bash
# PR 제출 전, 불필요한 커밋 정리
git rebase -i origin/main
```

편집기가 열리면:

```
pick a1b2c3 공식 프론트엔드 통합 완료
pick d4e5f6 프론트엔드 및 백엔드 연결 완료
pick 7890ab 리베이스 전 임시 저장        ← 이런 건 fixup 또는 drop
pick cdef12 맵 UI개선-중간 저장          ← 이런 건 fixup 또는 drop
pick 345678 맵 UI 개선_쿨로스터 체크방식 변경
```

`임시 저장`, `중간 저장` 앞의 `pick`을 `fixup`(또는 `f`)으로 바꾸면 해당 커밋은 앞 커밋에 흡수됩니다.

---

## 5. 커밋 메시지 기준

main에 들어오는 커밋은 아래 기준을 지켜야 합니다.

| 좋은 예 | 나쁜 예 |
|---------|---------|
| `feat: 맵 동 클릭 시 DongPanel 표시 추가` | `임시 저장` |
| `fix: StorePopup 렌더링 오류 수정` | `중간 저장` |
| `refactor: MapView 컴포넌트 분리` | `aaaaa` |

규칙: `타입: 한국어 설명`  
타입 목록: `feat` / `fix` / `refactor` / `chore` / `docs` / `style`

---

## 6. 이번 사건의 근본 원인 — Branch Protection

사실 이번 사건은 **시스템으로 막을 수 있었습니다.**

GitHub에는 "Branch Protection Rules"라는 기능이 있습니다.  
이것을 활성화하면 **PR 없이 main에 직접 push하는 것 자체가 차단됩니다.**

이번 사고를 계기로, **지금까지 설정만 해두고 활성화하지 않았던 보호 규칙을 즉시 활성화합니다.**

활성화 이후에는 아래와 같은 일이 불가능해집니다:

```bash
git push origin main          # ❌ 차단됨
git push origin main --force  # ❌ 차단됨
```

**main에 코드를 넣는 유일한 방법은 PR → 리뷰 → 머지** 뿐입니다.

---

## 7. 체크리스트 — 앞으로 작업 전 확인

```
□ 나는 지금 내 브랜치에 있는가? (main이 아닌가?)
□ 최신화가 필요하면 git rebase origin/main 을 썼는가?
□ 커밋 메시지가 "임시", "저장", "aaaa" 같은 표현이 없는가?
□ PR 전에 git rebase -i 로 커밋을 정리했는가?
□ push 대상이 내 브랜치인가? (origin/main이 아닌가?)
□ GitHub에서 PR을 열었는가?
```

---

## 마치며

이번 실수는 git에 익숙하지 않은 상태에서 충분히 일어날 수 있는 일입니다.  
중요한 건 **왜 문제인지 이해하고, 다음번에 반복하지 않는 것**입니다.

rebase가 낯설다면 `docs/plans/2026-04-01-git-rebase-guide.md`를 다시 한번 읽어보세요.  
모르는 것이 있으면 직접 물어보십시오.
