# Claude Code — CLI vs VSCode 익스텐션 하이브리드 운용

SOHOBI에서 Claude Code를 어떤 형태로 운용할지 결정하는 가이드. 두 가지 운용 형태(터미널 CLI / VSCode 익스텐션)의 장단을 비교하고, 프로젝트 워크플로우에 맞춘 하이브리드 셋업을 정리한다.

## 1. 한눈 비교

| 측면 | CLI | VSCode 익스텐션 |
| --- | --- | --- |
| 컨텍스트 인지 | 셸 cwd만 인지, 열린 파일·선택 영역 모름 | `ide_selection` 자동 전달, 열린 파일/선택 영역 활용 |
| 파일 네비게이션 | 텍스트 경로 출력 (`file.ts:42`) | 마크다운 링크 클릭 즉시 이동, diff 시각화 |
| 병렬 운용 | tmux/screen 분할로 가볍게 여러 세션 | 창 N개 → 메모리·스위칭 비용 |
| 장기 백그라운드 | `tmux detach`/`/schedule`/`/loop` 자연스러움 | IDE 종료 시 세션 끊김 위험 |
| 원격 환경 | SSH 위에서 그대로 작동 | Remote-SSH 의존, 네트워크 끊김 취약 |
| 자동화 친화 | shell pipeline·cron과 직접 결합 | IDE UI에 묶임 |
| diff·리뷰 UX | git CLI 텍스트 diff | inline diff·hover·peek 풍부 |
| 비기술 협업자 | 진입 장벽 높음 | 진입 장벽 낮음 |

## 2. SOHOBI 시나리오별 권장

| 시나리오 | 권장 | 이유 |
| --- | --- | --- |
| 메인 코드 작업·PR 리뷰 | VSCode 익스텐션 | 선택 영역·열린 파일·클릭 가능한 `[file:line]` 링크의 컨텍스트 우위 |
| 워크트리 병렬 운용 | CLI + tmux | IDE 창 N개의 메모리·인지 부담 회피, detach 가능 |
| `/schedule`·`/loop` 장기 자동화 | CLI 전용 | IDE 종료에 영향받지 않음 |
| Azure 장애 핫픽스 | 별도 터미널 CLI | 메인 IDE 작업 중단 없이 즉시 대응 |
| SSH 원격 작업 | CLI | 익스텐션은 Remote-SSH 끊김 위험 |
| 비기술 협업자 화면 공유 | VSCode 익스텐션 | 클릭·diff UX가 이해 쉬움 |

## 3. 하이브리드 셋업 (구체 명령)

### 워크트리 + CLI Claude 한 번에 띄우기

`~/.zshrc` 에 다음 함수 추가:

```bash
# 신규 워크트리 생성 + 그 폴더에서 CLI Claude를 tmux 세션으로 띄움
sohobi-tree() {
  local branch="$1"
  [[ -z "$branch" ]] && { echo "사용법: sohobi-tree <브랜치명>"; return 1; }
  local repo_root=~/Documents/GitHub/SOHOBI
  local wt_dir="$(dirname "$repo_root")/SOHOBI-${branch}"
  bash "$repo_root/scripts/worktree-setup.sh" "$branch" || return 1
  tmux new -A -s "sohobi-${branch}" -c "$wt_dir" "claude"
}

# 기존 워크트리 재진입 (tmux 세션 attach 또는 새로 생성)
sohobi-attach() {
  local repo_root=~/Documents/GitHub/SOHOBI
  local branch="${1:-$(git -C . branch --show-current 2>/dev/null)}"
  [[ -z "$branch" ]] && { echo "사용법: sohobi-attach <브랜치명>"; return 1; }
  local wt_dir="$(dirname "$repo_root")/SOHOBI-${branch}"
  [[ ! -d "$wt_dir" ]] && { echo "워크트리 없음: $wt_dir"; return 1; }
  tmux new -A -s "sohobi-${branch}" -c "$wt_dir" "claude"
}
```

### tmux 세션 명명 규칙

- 세션명: `sohobi-<브랜치명>`
- `tmux ls` 한 줄로 활성 워크트리 한눈에 확인
- detach: `Ctrl-b d` — IDE/터미널 닫혀도 세션 살아있음
- 재진입: `tmux attach -t sohobi-<브랜치명>` 또는 위 `sohobi-attach`

### VSCode 익스텐션 측 운용

- 메인 `SOHOBI/` 디렉토리만 IDE로 열어 둠 (브랜치는 main 유지가 자연스러움)
- 워크트리 작업은 IDE를 열지 않고 CLI에서만 진행 — IDE 컨텍스트가 다른 브랜치를 비추지 않게 분리
- 워크트리 PR 리뷰가 필요하면: 임시로 그 워크트리 폴더를 새 창으로 열되, 리뷰 후 닫음

## 4. 안티패턴

- IDE에서 `/schedule`·`/loop` 등록 후 IDE 종료 — 의도와 다르게 동작/중단될 수 있음. 장기 자동화는 반드시 CLI에서 등록한다.
- 워크트리마다 별도 VSCode 창을 띄움 — RAM·CPU 낭비, 알림·창 관리 비용 증가. CLI + tmux로 대체.
- CLI에서 큰 파일을 다중 탭으로 편집 — 마크다운 링크 클릭이 안 되어 비효율. 코드 편집 본진은 IDE.
- 같은 브랜치를 IDE와 CLI 양쪽에서 동시 편집 — git 충돌·파일 상태 혼란. 한 브랜치는 한 쪽에서만.

## 5. 빠른 결정 흐름

```
작업이 단일 브랜치 + 코드 편집/리뷰 중심?
  -> VSCode 익스텐션

작업이 여러 브랜치 동시 / 장기 자동화 / SSH 원격?
  -> CLI (+ tmux)

둘 다 해당?
  -> IDE는 메인, CLI는 워크트리·자동화 보조
```

## 6. 관련 문서

- [CLAUDE.md](../../CLAUDE.md) — 워크트리 병렬 운용 규칙, PR 라이프사이클 자동화
- [claude-code-guide.md](claude-code-guide.md) — 슬래시 명령 카탈로그
- [scripts/worktree-setup.sh](../../scripts/worktree-setup.sh) — 워크트리 환경 초기화 스크립트
