from fastapi import Request


def get_client_ip(request: Request) -> str:
    """X-Forwarded-For 마지막 hop → 실제 클라이언트 IP (Azure Container Apps 환경)."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"
