"""
SEC-005: Google OAuth state CSRF 방어 검증

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_oauth_state.py -v

state 쿠키/쿼리 검증 로직은 Google 토큰 교환 이전에 수행되므로 외부 HTTP 모킹 없이
상태 불일치 케이스를 검증할 수 있다. 양성 경로는 httpx.AsyncClient 를 patch 하여 검증.
"""

import importlib
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """GOOGLE_CLIENT_ID/SECRET 세팅 후 auth_router 재로드."""
    os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
    os.environ["JWT_SECRET"] = "test-jwt-secret"
    os.environ.pop("COSMOS_ENDPOINT", None)

    import auth_router

    importlib.reload(auth_router)

    app = FastAPI()
    app.include_router(auth_router.router)
    return TestClient(app)


class TestOAuthState:
    """/auth/google/callback state 검증"""

    def test_callback_missing_state_cookie_and_query(self, client):
        """state 쿠키·쿼리 모두 없음 → 400 + 잔존 쿠키 삭제"""
        resp = client.get(
            "/auth/google/callback",
            params={"code": "fake-code"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()
        # 에러 경로에서도 쿠키 삭제 헤더 발급
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie

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
        assert "Path=/auth" in set_cookie

    def test_callback_valid_state_completes_flow(self, client):
        """쿠키·쿼리 state 일치 → 토큰 교환 mock → 프론트 redirect + 쿠키 삭제"""
        # 1) /auth/google 호출하여 쿠키·state 획득
        login_resp = client.get("/auth/google", follow_redirects=False)
        assert login_resp.status_code in (302, 307)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state = qs["state"][0]
        # TestClient 의 cookie jar 가 Path 속성 매칭을 일관되게 처리하지 못하므로
        # 콜백 호출 전 명시적으로 쿠키를 세팅 (브라우저는 정상적으로 매칭함)
        client.cookies.set("oauth_state", state)

        # 2) httpx.AsyncClient 를 mock (token + userinfo 응답)
        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {"access_token": "fake-token"}
        mock_info_resp = MagicMock(status_code=200)
        mock_info_resp.json.return_value = {
            "sub": "test-sub",
            "email": "t@e.com",
            "name": "Tester",
            "picture": "",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_token_resp)
        mock_client.get = AsyncMock(return_value=mock_info_resp)
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        import auth_router

        with patch.object(auth_router.httpx, "AsyncClient", return_value=mock_client):
            resp = client.get(
                "/auth/google/callback",
                params={"code": "fake-code", "state": state},
                follow_redirects=False,
            )

        assert resp.status_code in (302, 307)
        assert "/auth/callback#token=" in resp.headers["location"]
        # 성공 경로에서도 쿠키 삭제
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie

    def test_callback_token_exchange_failure_clears_cookie(self, client):
        """토큰 교환 실패 → 400 + state 쿠키 삭제 (성공/state-mismatch 경로와 대칭)"""
        login_resp = client.get("/auth/google", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state = qs["state"][0]
        client.cookies.set("oauth_state", state)

        mock_token_resp = MagicMock(status_code=500)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_token_resp)
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        import auth_router

        with patch.object(auth_router.httpx, "AsyncClient", return_value=mock_client):
            resp = client.get(
                "/auth/google/callback",
                params={"code": "fake-code", "state": state},
                follow_redirects=False,
            )

        assert resp.status_code == 400
        assert "토큰 교환" in resp.json()["detail"]
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie

    def test_delete_cookie_has_security_attrs(self, client):
        """에러 경로 delete_cookie 는 set_cookie 와 동일하게 Secure/SameSite/HttpOnly/Path=/auth 포함."""
        resp = client.get(
            "/auth/google/callback",
            params={"code": "fake-code"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=lax" in set_cookie
        assert "HttpOnly" in set_cookie

    def test_callback_501_clears_state_cookie(self, monkeypatch):
        """_GOOGLE_CLIENT_ID 미설정 → 501 + 잔존 state 쿠키 삭제 (HTTPException 대신 JSONResponse)."""
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["JWT_SECRET"] = "test-jwt-secret"
        os.environ.pop("COSMOS_ENDPOINT", None)

        import auth_router

        importlib.reload(auth_router)
        monkeypatch.setattr(auth_router, "_GOOGLE_CLIENT_ID", "")

        app = FastAPI()
        app.include_router(auth_router.router)
        tc = TestClient(app)
        tc.cookies.set("oauth_state", "stale-value")

        resp = tc.get(
            "/auth/google/callback",
            params={"code": "fake-code", "state": "anything"},
            follow_redirects=False,
        )
        assert resp.status_code == 501
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie
        assert "Max-Age=0" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=lax" in set_cookie

    def test_state_mismatch_log_includes_client_ip(self, client, caplog):
        """OAUTH_STATE_MISMATCH 경고에 client_ip=... 포맷 포함.

        sohobi.security 로거는 propagate=False 이므로 caplog 의 root handler 만으로는
        capture 되지 않는다. caplog.handler 를 해당 로거에 직접 attach 한다.
        """
        security_logger = logging.getLogger("sohobi.security")
        security_logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.WARNING, logger="sohobi.security"):
                resp = client.get(
                    "/auth/google/callback",
                    params={"code": "fake-code"},
                    follow_redirects=False,
                )
        finally:
            security_logger.removeHandler(caplog.handler)
        assert resp.status_code == 400
        mismatch_records = [
            r for r in caplog.records if "OAUTH_STATE_MISMATCH" in r.getMessage()
        ]
        assert mismatch_records, "OAUTH_STATE_MISMATCH log expected"
        assert "client_ip=" in mismatch_records[0].getMessage()

    def test_callback_userinfo_failure_clears_cookie(self, client):
        """userinfo 조회 실패 → 400 + state 쿠키 삭제"""
        login_resp = client.get("/auth/google", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state = qs["state"][0]
        client.cookies.set("oauth_state", state)

        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {"access_token": "fake-token"}
        mock_info_resp = MagicMock(status_code=500)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_token_resp)
        mock_client.get = AsyncMock(return_value=mock_info_resp)
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        import auth_router

        with patch.object(auth_router.httpx, "AsyncClient", return_value=mock_client):
            resp = client.get(
                "/auth/google/callback",
                params={"code": "fake-code", "state": state},
                follow_redirects=False,
            )

        assert resp.status_code == 400
        assert "유저 정보" in resp.json()["detail"]
        set_cookie = resp.headers.get("set-cookie", "")
        assert "oauth_state=" in set_cookie
        assert "Path=/auth" in set_cookie
