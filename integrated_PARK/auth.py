"""
API Key 인증 의존성.

환경변수 API_SECRET_KEY 가 설정된 경우에만 활성화된다.
미설정 시(로컬 개발·테스트) 모든 요청을 통과시킨다.

사용법:
    from auth import verify_api_key
    from fastapi import Depends

    @app.post("/api/v1/query", dependencies=[Depends(verify_api_key)])
    async def query(...): ...
"""

import hmac
import os

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_API_KEY = os.getenv("API_SECRET_KEY", "")
_security = HTTPBearer(auto_error=False)


def verify_api_key(
    authorization: HTTPAuthorizationCredentials | None = Depends(_security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    Bearer 토큰 또는 X-API-Key 헤더로 API Key를 검증한다.
    API_SECRET_KEY 환경변수가 비어있으면 검증을 건너뛴다 (개발 모드).
    """
    if not _API_KEY:
        return  # 개발 모드: 환경변수 미설정 시 통과

    token: str | None = None
    if authorization:
        token = authorization.credentials
    elif x_api_key:
        token = x_api_key

    if not token or not hmac.compare_digest(token, _API_KEY):
        raise HTTPException(status_code=401, detail="인증 필요")
