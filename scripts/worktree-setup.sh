#!/usr/bin/env bash
# worktree-setup.sh — SOHOBI 워크트리 생성 + 환경 초기화
#
# 사용법:
#   ./scripts/worktree-setup.sh <브랜치명> [base-branch]
#
# 예시:
#   ./scripts/worktree-setup.sh PARK-fix-login            # origin/main 기반
#   ./scripts/worktree-setup.sh PARK-review-231 pr-branch  # 기존 브랜치 체크아웃
#
# 생성 위치: ../SOHOBI-<브랜치명>/

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"
PARENT_DIR="$(dirname "$REPO_ROOT")"

if [[ $# -lt 1 ]]; then
  echo "사용법: $0 <브랜치명> [base-branch]"
  echo "  base-branch 생략 시 origin/main 기반 새 브랜치 생성"
  exit 1
fi

BRANCH="$1"
BASE="${2:-origin/main}"
WORKTREE_DIR="${PARENT_DIR}/${REPO_NAME}-${BRANCH}"

# 중복 확인
if [[ -d "$WORKTREE_DIR" ]]; then
  echo "오류: ${WORKTREE_DIR} 이미 존재합니다."
  echo "  기존 워크트리 사용: cd ${WORKTREE_DIR}"
  echo "  제거 후 재생성:     git worktree remove ${WORKTREE_DIR}"
  exit 1
fi

# 최신 원격 정보 가져오기
echo "==> git fetch origin"
git -C "$REPO_ROOT" fetch origin

# 워크트리 생성
if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/${BRANCH}" 2>/dev/null || \
   git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/${BRANCH}" 2>/dev/null; then
  # 기존 브랜치 체크아웃
  echo "==> 기존 브랜치 '${BRANCH}' 체크아웃"
  git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" "$BRANCH"
else
  # 새 브랜치 생성
  echo "==> 새 브랜치 '${BRANCH}' 생성 (base: ${BASE})"
  git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WORKTREE_DIR" "$BASE"
fi

# .env 복사 (backend)
if [[ -f "${REPO_ROOT}/backend/.env" ]]; then
  cp "${REPO_ROOT}/backend/.env" "${WORKTREE_DIR}/backend/.env"
  echo "==> backend/.env 복사 완료"
fi

# .env 복사 (frontend, 있는 경우)
if [[ -f "${REPO_ROOT}/frontend/.env" ]]; then
  cp "${REPO_ROOT}/frontend/.env" "${WORKTREE_DIR}/frontend/.env"
  echo "==> frontend/.env 복사 완료"
fi

# 프론트엔드 의존성 설치
if [[ -f "${WORKTREE_DIR}/frontend/package.json" ]]; then
  echo "==> frontend npm install"
  (cd "${WORKTREE_DIR}/frontend" && npm install --silent)
fi

# 백엔드 venv 생성 + 의존성 설치
if [[ -f "${WORKTREE_DIR}/backend/requirements.txt" ]]; then
  echo "==> 백엔드 venv 생성 및 의존성 설치"
  python3 -m venv "${WORKTREE_DIR}/backend/.venv"
  "${WORKTREE_DIR}/backend/.venv/bin/pip" install -q -r "${WORKTREE_DIR}/backend/requirements.txt"
fi

echo ""
echo "워크트리 생성 완료!"
echo "  경로:   ${WORKTREE_DIR}"
echo "  브랜치: ${BRANCH}"
echo ""
echo "다음 단계:"
echo "  cd ${WORKTREE_DIR}"
echo "  # VS Code: code ${WORKTREE_DIR}"
echo "  # Claude Code 세션을 이 디렉토리에서 시작하면 독립 작업 가능"
