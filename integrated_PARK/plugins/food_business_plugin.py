"""
식품 영업 신고서 PDF 생성 플러그인
출처: NAM/BusinessPlugin.py + NAM/overlay_main.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function

# NAM 폴더의 overlay_main(픽셀 정밀 PDF 생성기) 참조
_NAM_DIR = Path(__file__).parent.parent / "nam"
if str(_NAM_DIR) not in sys.path:
    sys.path.insert(0, str(_NAM_DIR))


class FoodBusinessPlugin:
    """
    식품 관련 행정 서류 처리 플러그인.
    사용자 정보를 JSON으로 받아 식품 영업 신고서 PDF를 생성한다.
    """

    def __init__(self, output_dir: str = "."):
        self._output_dir = output_dir
        # original.pdf 경로: NAM 폴더 기준
        self._original_pdf = str(_NAM_DIR / "original.pdf")

    @kernel_function(
        name="create_food_report",
        description=(
            "사용자의 인적사항과 매장 정보를 바탕으로 "
            "관공서 양식에 맞춘 식품 영업 신고서 PDF를 생성합니다."
        ),
    )
    def create_food_report(
        self,
        json_input: Annotated[
            str,
            """수집된 정보를 담은 JSON 문자열 (1-depth 평탄화 객체):
            {"owner_name": "...", "owner_ssn": "...", "owner_address": "...",
             "owner_phone": "...", "store_name": "...", "store_phone": "...",
             "business_type": "...", "area_size": "...", "area_outside": "...",
             "store_address": "...", "submit_year": "2026",
             "submit_month": "03", "submit_day": "11"}""",
        ],
    ) -> str:
        try:
            import overlay_main  # NAM/overlay_main.py

            clean = json_input.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.endswith("```"):
                clean = clean[:-3]
            data = json.loads(clean.strip())

            output_pdf = os.path.join(
                self._output_dir,
                f"영업신고서_{data.get('store_name', '매장')}.pdf",
            )
            overlay_main.merge_pdf(
                original_pdf_path=self._original_pdf,
                output_path=output_pdf,
                data=data,
            )
            return (
                f"✅ 서류 생성 완료. "
                f"'{output_pdf}' 파일이 생성되었습니다."
            )
        except json.JSONDecodeError as e:
            return f"❌ JSON 파싱 오류: {e}"
        except Exception as e:
            return f"❌ PDF 생성 오류: {e}"
