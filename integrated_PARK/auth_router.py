"""
Google OAuth 2.0 소셜 로그인 + JWT 발급 라우터.

엔드포인트:
  GET  /auth/google              — Google 인증 페이지로 redirect
  GET  /auth/google/callback     — OAuth code 교환 → user upsert → JWT → 프론트 redirect
  GET  /auth/me                  — 현재 로그인 유저 정보 반환
  POST /auth/link-session        — 익명 session_id를 현재 유저에 귀속

환경변수 (integrated_PARK/.env):
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  JWT_SECRET
  JWT_ALGORITHM   (기본값 HS256)
  JWT_EXPIRE_HOURS (기본값 720 = 30일)
  FRONTEND_URL    (기본값 http://localhost:5173)
"""

import os
import time
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# ── 설정 ─────────────────────────────────────────────────────────
_GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "720"))
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
_BACKEND_URL = os.getenv("BACKEND_HOST", "http://localhost:8000")

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_security = HTTPBearer(auto_error=False)


# ── Cosmos users 컨테이너 ─────────────────────────────────────────
_users_container = None


async def _get_users_container():
    global _users_container
    if _users_container is not None:
        return _users_container

    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None

    from azure.cosmos.aio import CosmosClient
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")
    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)
    _users_container = db.get_container_client("users")
    return _users_container


# ── 인메모리 폴백 (로컬 개발용) ──────────────────────────────────
_users_memory: dict[str, dict] = {}


# ── JWT 유틸 ─────────────────────────────────────────────────────


def _create_jwt(user_id: str, email: str, name: str, picture: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=_JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "exp": expire,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _decode_jwt(token: str) -> dict:
    return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])


# ── 현재 유저 의존성 ─────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    """JWT가 유효하면 payload 반환. 없거나 잘못되면 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    try:
        payload = _decode_jwt(credentials.credentials)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict | None:
    """JWT가 있고 유효하면 payload 반환, 없으면 None (비회원 허용)."""
    if credentials is None:
        return None
    try:
        return _decode_jwt(credentials.credentials)
    except JWTError:
        return None


# ── user upsert ───────────────────────────────────────────────────


async def _upsert_user(user_id: str, email: str, name: str, picture: str) -> dict:
    user = {
        "id": user_id,
        "provider": "google",
        "email": email,
        "name": name,
        "picture": picture,
        "created_at": datetime.now(UTC).isoformat(),
    }
    container = await _get_users_container()
    if container is None:
        if user_id not in _users_memory:
            _users_memory[user_id] = user
        return _users_memory[user_id]

    try:
        existing = await container.read_item(item=user_id, partition_key=user_id)
        # 이름/사진만 업데이트 (created_at 보존)
        existing.update({"name": name, "picture": picture, "email": email})
        await container.replace_item(item=user_id, body=existing)
        return existing
    except Exception:
        await container.upsert_item(user)
        return user


# ── 엔드포인트 ───────────────────────────────────────────────────


@router.get("/google")
async def google_login():
    """Google OAuth 인증 페이지로 redirect."""
    if not _GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth 미설정")

    redirect_uri = f"{_BACKEND_URL}/auth/google/callback"
    params = (
        f"client_id={_GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return RedirectResponse(url=f"{_GOOGLE_AUTH_URL}?{params}")


@router.get("/google/callback")
async def google_callback(code: str = Query(...)):
    """Google OAuth code → 토큰 교환 → 유저 upsert → JWT 발급 → 프론트 redirect."""
    if not _GOOGLE_CLIENT_ID or not _GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth 미설정")

    redirect_uri = f"{_BACKEND_URL}/auth/google/callback"

    async with httpx.AsyncClient() as client:
        # code → access_token 교환
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "client_id": _GOOGLE_CLIENT_ID,
                "client_secret": _GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Google 토큰 교환 실패")

        access_token = token_resp.json().get("access_token", "")

        # userinfo 조회
        info_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Google 유저 정보 조회 실패")

    info = info_resp.json()
    sub = info.get("sub", "")
    email = info.get("email", "")
    name = info.get("name", "")
    picture = info.get("picture", "")
    user_id = f"google:{sub}"

    await _upsert_user(user_id, email, name, picture)
    token = _create_jwt(user_id, email, name, picture)

    # 프론트엔드로 redirect (token은 URL fragment로 전달)
    return RedirectResponse(url=f"{_FRONTEND_URL}/auth/callback#token={token}")


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """현재 로그인 유저 정보 반환."""
    return {
        "user_id": user["sub"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
    }


class LinkSessionRequest(BaseModel):
    session_id: str


@router.post("/link-session")
async def link_session(
    req: LinkSessionRequest,
    user: dict = Depends(get_current_user),
):
    """익명 session_id를 현재 유저에 귀속하고 TTL을 무기한으로 연장."""
    import session_store

    await session_store.link_session_to_user(req.session_id, user["sub"])
    return {"ok": True, "session_id": req.session_id, "user_id": user["sub"]}


# ── 공용: user_id → {email, name} 조회 (캐시 포함) ─────────────────

_USER_INFO_CACHE: dict[str, tuple[float, dict]] = {}
_USER_INFO_CACHE_TTL = 300  # 5분


async def get_user_info(user_id: str) -> dict:
    """user_id로 {email, name} 조회. Cosmos users 컨테이너 사용, 5분 캐시."""
    if not user_id:
        return {}
    now = time.time()
    if user_id in _USER_INFO_CACHE:
        expires_at, cached = _USER_INFO_CACHE[user_id]
        if expires_at > now:
            return cached

    container = await _get_users_container()
    if container is None:
        user = _users_memory.get(user_id, {})
        result = {"email": user.get("email", ""), "name": user.get("name", "")}
    else:
        try:
            item = await container.read_item(item=user_id, partition_key=user_id)
            result = {"email": item.get("email", ""), "name": item.get("name", "")}
        except Exception:
            result = {}

    _USER_INFO_CACHE[user_id] = (now + _USER_INFO_CACHE_TTL, result)
    return result
