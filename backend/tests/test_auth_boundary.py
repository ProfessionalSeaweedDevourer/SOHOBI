"""
PR-A 인증·세션 경계 검증 (SEC-001 / SEC-003 / SEC-004).

커버리지:
  T-AB-01  APP_ENV=production + JWT_SECRET 미설정 → startup 실패
  T-AB-02  user_id 가 박힌 세션을 무인증 GET /api/report/{sid} → 403
  T-AB-03  user_id 가 박힌 세션을 다른 사용자 JWT 로 PATCH /api/checklist/{sid} → 403
  T-AB-04  이미 user_A 에 귀속된 세션을 user_B 가 link-session → 409

Cosmos 의존을 피하기 위해 `COSMOS_ENDPOINT` 미설정 상태(인메모리 폴백)로
테스트하고, `session_store._memory` 에 직접 세션 픽스처를 주입한다.
"""

import os

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport
from semantic_kernel.contents import ChatHistory

import session_store
from auth_router import _create_jwt, router as auth_router
from checklist_router import router as checklist_router
from report_router import router as report_router


# ── 공통 픽스처 ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    """모든 테스트에서 JWT 서명 가능하도록 고정 시크릿 주입."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-auth-boundary")
    # API 키 검증 모듈을 강제로 비활성화 (모듈 로드 시점에 캡처된 값 교체)
    import auth

    monkeypatch.setattr(auth, "_API_KEY", "", raising=False)
    # Cosmos 미설정 상태 강제 (인메모리 폴백)
    monkeypatch.delenv("COSMOS_ENDPOINT", raising=False)


@pytest.fixture(autouse=True)
def _reset_memory_store():
    """테스트 간 인메모리 세션/유저 스토어 초기화."""
    session_store._memory.clear()
    # auth_router 도 자체 users 메모리를 가짐
    from auth_router import _users_memory

    _users_memory.clear()
    yield
    session_store._memory.clear()
    _users_memory.clear()


def _build_app() -> FastAPI:
    """api_server 전체를 import 하지 않고 필요한 라우터만 포함한 테스트 앱."""
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(checklist_router)
    app.include_router(report_router)
    return app


def _inject_session(session_id: str, user_id: str | None) -> None:
    """인메모리 스토어에 세션을 주입. user_id 가 None 이면 익명."""
    sess = {
        "profile": "",
        "history": ChatHistory(),
        "extracted": {},
        "context": {"adm_codes": [], "business_type": "", "location_name": ""},
    }
    if user_id:
        sess["user_id"] = user_id
    session_store._memory[session_id] = sess


def _jwt_for(user_id: str) -> str:
    return _create_jwt(user_id, f"{user_id}@test.local", user_id, "")


# ── T-AB-01: startup 검증 ─────────────────────────────────────────


def test_ab_01_startup_requires_jwt_secret_in_non_local(monkeypatch):
    """APP_ENV=production 이고 JWT_SECRET 미설정이면 RuntimeError."""
    from api_server import _validate_startup_env

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _validate_startup_env()


def test_ab_01_startup_allows_local_without_jwt_secret(monkeypatch):
    """APP_ENV=local 이면 JWT_SECRET 미설정이어도 통과 (개발 편의)."""
    from api_server import _validate_startup_env

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    _validate_startup_env()  # no exception


# ── T-AB-02 ~ T-AB-04: 엔드포인트 경계 ────────────────────────────


@pytest.mark.asyncio
async def test_ab_02_report_of_owned_session_denies_anon():
    """user_id 가 박힌 세션을 무인증으로 GET → 403."""
    sid = "sess-owned-by-user-a"
    _inject_session(sid, user_id="google:user-a")

    app = _build_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/report/{sid}")

    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_ab_02_report_of_anonymous_session_still_works():
    """user_id 가 없는 익명 세션은 기존대로 통과 (회귀 없음)."""
    sid = "sess-anonymous"
    _inject_session(sid, user_id=None)

    app = _build_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/report/{sid}")

    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_ab_03_patch_checklist_with_other_user_jwt_is_forbidden():
    """user_A 소유 세션을 user_B 의 JWT 로 PATCH → 403."""
    sid = "sess-owned-by-user-a"
    _inject_session(sid, user_id="google:user-a")
    other_token = _jwt_for("google:user-b")

    app = _build_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/checklist/{sid}",
            json={"item_id": "business_plan", "checked": True, "source": "manual"},
            headers={"Authorization": f"Bearer {other_token}"},
        )

    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_ab_04_link_session_reassignment_returns_409():
    """이미 user_A 에 귀속된 세션을 user_B 가 링크 시도 → 409."""
    sid = "sess-linked-to-user-a"
    _inject_session(sid, user_id="google:user-a")
    user_b_token = _jwt_for("google:user-b")

    app = _build_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/link-session",
            json={"session_id": sid},
            headers={"Authorization": f"Bearer {user_b_token}"},
        )

    assert resp.status_code == 409, resp.text
    # 세션의 귀속은 변하지 않아야 함
    assert session_store._memory[sid]["user_id"] == "google:user-a"


@pytest.mark.asyncio
async def test_ab_04_link_session_is_idempotent_for_same_user():
    """동일 user 재링크는 200 (idempotent)."""
    sid = "sess-linked-to-user-a"
    _inject_session(sid, user_id="google:user-a")
    user_a_token = _jwt_for("google:user-a")

    app = _build_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/link-session",
            json={"session_id": sid},
            headers={"Authorization": f"Bearer {user_a_token}"},
        )

    assert resp.status_code == 200, resp.text
