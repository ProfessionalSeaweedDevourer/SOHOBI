"""sohobi.security 로거 명시 설정.

목적:
- 보안 이벤트(OAUTH_*, IP_BLOCKED, INJECTION_SUSPECT, DOMAIN_OVERRIDE)를
  일반 로그와 구분되는 [SECURITY] 프리픽스로 stderr 출력
- 추후 SIEM/알림 sink 분리 시 단일 변경 지점 확보
- propagate=False 로 루트 로거 중복 출력 차단
"""

import logging
import sys

_CONFIGURED = False


def configure_security_logger() -> None:
    """sohobi.security 로거에 stderr StreamHandler + 보안 전용 포맷 부착.

    api_server.py 시작 시 1회 호출. idempotent — 재호출 시 핸들러 중복 부착 없음.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger = logging.getLogger("sohobi.security")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[SECURITY] %(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _CONFIGURED = True
