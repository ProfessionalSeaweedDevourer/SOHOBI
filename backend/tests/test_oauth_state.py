"""
SEC-005: Google OAuth state CSRF 방어 검증

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_oauth_state.py -v

state 쿠키/쿼리 검증 로직은 Google 토큰 교환 이전에 수행되므로 외부 HTTP 모킹 없이
상태 불일치 케이스를 검증할 수 있다.
"""

import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """GOOGLE_CLIENT_ID/SECRET 세팅 후 auth_router 재로드."""
    os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
    os.environ["JWT_SECRET"] = "test-jwt-secret"

    import auth_router

    importlib.reload(auth_router)

    app = FastAPI()
    app.include_router(auth_router.router)
    return TestClient(app)


class TestOAuthState:
    """/auth/google/callback state 검증"""

    def test_callback_missing_state_cookie_and_query(self, client):
        """state 쿠키·쿼리 모두 없음 → 400"""
        resp = client.get(
            "/auth/google/callback",
            params={"code": "fake-code"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()

    def test_callback_cookie_but_no_query_state(self, client):
        """쿠키는 있는데 쿼리 state 없음 → 400"""
        client.cookies.set("oauth_state", "cookie-value")
        resp = client.get(
            "/auth/google/callback",
            params={"code": "fake-code"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()

    def test_callback_state_mismatch(self, client):
        """쿠키와 쿼리 state 불일치 → 400"""
        client.cookies.set("oauth_state", "cookie-value")
        resp = client.get(
            "/auth/google/callback",
            params={"code": "fake-code", "state": "different-value"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()

    def test_google_login_sets_state_cookie_and_url(self, client):
        """/auth/google 진입 → state 쿠키 Set-Cookie + URL state 파라미터 포함"""
        resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code in (302, 307)

        location = resp.headers.get("location", "")
        assert "state=" in location

        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
