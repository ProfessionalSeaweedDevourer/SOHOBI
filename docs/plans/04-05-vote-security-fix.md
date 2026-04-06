# 세션 4 작업 계획 — 투표 보안 취약점 수정

## Context

이전 세션(3E)에서 로드맵 투표 기능을 구현했으나, `POST /api/roadmap/vote` 엔드포인트에 보안 취약점이 발견됨:
- `session_id`를 클라이언트에서 받지만 **실제 존재 여부를 검증하지 않음**
- 로그인 사용자와 비로그인 사용자를 구분하지 않아 **동일 유저가 다른 session_id로 중복 투표** 가능

PR #146 (오픈 중)에 이전 세션 작업이 포함되어 있음. 이 세션은 해당 PR 머지 후 보안 수정 작업을 진행함.

---

## 작업 순서

### Task 0: PR #146 상태 확인 및 머지

- `gh pr view 146` 로 빌드/리뷰 상태 확인
- 머지 가능하면 사용자에게 머지 요청

---

### Task 1: 투표 보안 수정 — 2단계 적용

**대상 파일**: `integrated_PARK/roadmap_router.py`

#### 1-A: `get_optional_user` 의존성 추가 (로그인 유저 판별)

`toggle_vote()` 함수 시그니처 변경:

```python
# 현재
async def toggle_vote(req: VoteRequest):

# 변경 후
async def toggle_vote(
    req: VoteRequest,
    user: dict | None = Depends(get_optional_user),
):
```

`auth_router.py`에서 `get_optional_user` import 추가.

#### 1-B: 투표 식별자 결정 로직 추가

```python
if user:
    # 로그인 유저: user_id 기반 (JWT sub 필드)
    voter_id = f"user_{user['sub']}"
else:
    # 비로그인: session_id 사용 (유효성 검증 후)
    voter_id = f"session_{req.session_id}"

doc_id = f"vote_{fid}_{voter_id}"
```

#### 1-C: session_id 유효성 검증 (비로그인 경우)

```python
if not user:
    session = await get_query_session(req.session_id)
    if not session.get("messages"):
        raise HTTPException(status_code=400, detail="유효하지 않은 session_id")
```

- `session_store.get_query_session()`은 존재하지 않는 session_id에 대해 빈 dict 반환
- `messages` 키 존재 여부로 유효성 판단

#### 1-D: `get_roadmap_votes()` 동일 로직 적용

사용자의 투표 상태 조회 시에도 같은 voter_id 계산 로직 적용.

---

### Task 2: 프론트엔드 — 로그인 상태에 따른 투표 UX 개선

**대상 파일**: `frontend/src/pages/Roadmap.jsx` (또는 투표 UI 컴포넌트)

- 로그인 상태일 때: 정상 투표
- 비로그인 상태일 때: session_id 없거나 채팅 전이면 "채팅 후 투표 가능" 안내 표시

---

## 핵심 파일

| 파일 | 역할 | 변경 여부 |
|------|------|---------|
| `integrated_PARK/roadmap_router.py` | toggle_vote, get_roadmap_votes | **수정** |
| `integrated_PARK/auth_router.py` | get_optional_user 제공 | import만 |
| `integrated_PARK/session_store.py` | get_query_session 사용 | import만 |
| `frontend/src/pages/Roadmap.jsx` | 투표 UX | **확인 후 수정** |

---

## 재사용할 기존 함수

- `auth_router.get_optional_user` — JWT 있으면 payload, 없으면 None
- `session_store.get_query_session(session_id)` — 세션 존재 여부 확인용

---

## 검증 TC

| TC | 내용 | 기대 결과 |
|----|------|---------|
| TC1 | 비로그인 + 유효 session_id → 투표 | ✅ 200 |
| TC2 | 비로그인 + 가짜 session_id → 투표 | ❌ 400 |
| TC3 | 로그인 + 투표 → user_id 기반 중복 방지 | ✅ 토글 |
| TC4 | 로그인 + 다른 session_id로 재투표 시도 | ❌ 중복 방지 (user_id 동일) |
| TC5 | 기존 투표 현황 조회 정상 동작 | ✅ 200 |
