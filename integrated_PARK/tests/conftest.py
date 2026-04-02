"""
pytest conftest.py — integrated_PARK/tests/ 공통 설정

sys.path에 integrated_PARK/ 루트를 추가하여 모든 테스트에서
agents, plugins, signoff 모듈을 직접 import할 수 있도록 합니다.
"""

import sys
import os
from dotenv import load_dotenv

# integrated_PARK/ 디렉토리를 sys.path 최상위에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# integrated_PARK/.env 를 pytest 수집 전에 로드 (skipif 조건 평가에 반영됨)
load_dotenv(os.path.join(_ROOT, ".env"))
