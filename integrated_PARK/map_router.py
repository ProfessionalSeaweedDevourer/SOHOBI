"""
지도 데이터 라우터 (마이그레이션 완료)

모든 엔드포인트가 아래 두 router로 이전됨:
  - map_data_router.py  : /map/* (WOO DAO 기반 실구현)
  - realestate_router.py: /realestate/* (WOO DAO 기반 실구현)

api_server.py에서 이 파일을 계속 import하므로 빈 router를 유지함.
"""

from fastapi import APIRouter

router = APIRouter()
