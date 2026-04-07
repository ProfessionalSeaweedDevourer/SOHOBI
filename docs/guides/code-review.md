# 코드 리뷰 가이드

매 PR마다 Claude가 수행하는 코드 리뷰 절차와 판단 기준.

---

## 1. 정보 수집 (읽기 전용)

```bash
# PR 메타데이터 + 머지 가능성
gh pr view <N> --json title,body,author,headRefName,mergeable,mergeStateStatus,files

# 전체 diff
gh pr diff <N>

# CI 상태
gh pr checks <N>

# 브랜치 커밋 현황 (stale 커밋 여부)
git fetch origin
git log --oneline origin/main...<headBranch> --left-right
```

---

## 2. 분석 체크리스트

| 항목 | 확인 방법 |
|------|---------|
| 기술적 머지 가능성 | `mergeable`, `mergeStateStatus` |
| stale 커밋 (squash 재노출) | `git log --left-right` |
| CI PASS | `gh pr checks` |
| 변경 파일 전체 읽기 | Read tool |
| 버그 — 모바일/반응형 | CSS specificity 충돌, 미디어 쿼리 vs 인라인 스타일 |
| 버그 — 상태 의존성 | prop drilling 누락, `useCallback` deps 배열 |
| 마법 상수 결합도 | 하드코딩 숫자가 다른 파일 값과 암묵적으로 연결? |
| 에셋/임포트 존재 | `Glob` 확인 |
| UX 회귀 | 기본 동작 변경이 기존 사용자 경험을 해치는가 |

---

## 3. 이슈 심각도

| 등급 | 기준 | 예시 |
|------|------|------|
| 🔴 High | 재현 가능한 버그, 기능 깨짐 | 모바일에서 레이아웃 찌그러짐, null 참조 에러 |
| 🟡 Medium | 잠재적 버그, 결합도 문제, 규칙 위반 | 매직 넘버 결합, rebase 누락, 중복 로직 |
| 🟢 Low | 스타일 제안, UX 논의, 개선 기회 | 변수명, 조건부 UX 개선 제안 |

---

## 4. 리뷰 결정 기준

| 결정 | 조건 |
|------|------|
| `APPROVE` | High/Medium 이슈 없음, rebase 완료, CI PASS |
| `REQUEST_CHANGES` | High 버그 존재 또는 rebase 미완료 |
| `COMMENT` | Low 이슈만 있을 때 (블로커 없음) |

---

## 5. 코멘트 작성

```bash
# 전체 리뷰 (권장)
gh pr review <N> --request-changes --body "..."
gh pr review <N> --approve --body "..."
gh pr review <N> --comment --body "..."

# 인라인 코멘트 (특정 줄)
COMMIT_SHA=$(gh pr view <N> --json headRefOid -q .headRefOid)
gh api repos/ProfessionalSeaweedDevourer/SOHOBI/pulls/<N>/comments \
  --method POST \
  --field body="..." \
  --field commit_id="$COMMIT_SHA" \
  --field path="경로/파일.jsx" \
  --field line=<줄번호> \
  --field side="RIGHT"
```

---

## 6. 교통정리 결정 트리

```
이슈 발견
├── Low only              → COMMENT + APPROVE
├── Medium (버그 없음)    → REQUEST_CHANGES + 코멘트 안내
├── High (버그)
│   ├── author가 수정 가능 → REQUEST_CHANGES + 코멘트 안내
│   └── 내가 직접 수정    → 해당 브랜치 checkout → 커밋 추가 → push
└── 충돌 발생
    ├── 단순 충돌          → rebase 안내 코멘트
    └── 복잡한 충돌        → 별도 정리 PR 생성
```

---

## 7. stale 커밋 / rebase 안내 문구 (재사용)

```
CHOI2 브랜치에 PR #XXX에서 이미 squash-merge된 커밋이 남아 있습니다.
머지 전 rebase가 필요합니다 (CLAUDE.md Rebase 기반 워크플로우 참조):

git fetch origin
git rebase origin/main
# "patch contents already upstream" → git rebase --skip
git push --force-with-lease origin <브랜치>
```

---

## 8. 검증 (리뷰 후)

```bash
# 리뷰 상태 확인
gh pr view <N> --json reviews --jq '.reviews[-1].state'

# author 수정 후 재확인
gh pr checks <N>
```

UI 변경 포함 시: Vercel preview URL에서 playwright `browser_navigate` → `browser_snapshot` 으로 TC 검증.
