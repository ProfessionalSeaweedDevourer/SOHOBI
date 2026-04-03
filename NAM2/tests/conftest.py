"""
pytest conftest.py — NAM2/tests/ 공통 설정
NAM2/ 루트를 sys.path에 추가하여 GovSupportPlugin을 직접 import 가능하게 합니다.
"""

import sys
import os

_NAM2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _NAM2_ROOT not in sys.path:
    sys.path.insert(0, _NAM2_ROOT)
