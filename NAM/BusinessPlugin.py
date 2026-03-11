from semantic_kernel.functions import kernel_function
from typing import Annotated
import json
import os
import overlay_main # 대은님의 완벽한 픽셀 PDF 생성기

class FoodBusinessPlugin:
    """식품 관련 행정 서류 처리를 담당하는 전문 플러그인"""

    @kernel_function(
        name="create_food_report",
        description="사용자의 인적사항과 매장 정보를 바탕으로 관공서 양식에 맞춘 '식품 영업 신고서 PDF'를 생성합니다."
    )
    def create_food_report(
        self, 
        json_input: Annotated[str, """수집된 정보를 담은 JSON 문자열. 
        반드시 1 depth의 평탄화된 단일 JSON 객체로 아래 영문 키를 정확히 사용하세요:
        {"owner_name": "...", "owner_ssn": "...", "owner_address": "...", "owner_phone": "...", "store_name": "...", "store_phone": "...", "business_type": "...", "area_size": "...", "area_outside": "...", "store_address": "...", "submit_year": "2026", "submit_month": "03", "submit_day": "11"}"""]
    ) -> str:
        
        try:
            # 1. 마크다운 찌꺼기 제거
            clean_json = json_input.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            # 2. JSON 변환 (데이터 파싱)
            data = json.loads(clean_json)
            print(f"\n✅ [시스템 상황판] 에이전트가 조립한 PDF 데이터:\n{json.dumps(data, ensure_ascii=False, indent=2)}\n")

            # 3. 대은님의 PDF 생성기 직접 실행! (이게 터미널에서 잘 되던 핵심입니다)
            original_pdf = "original.pdf"
            output_pdf = f"영업신고서_{data.get('store_name', '매장')}.pdf"
            
            overlay_main.merge_pdf(
                original_pdf_path=original_pdf,
                output_path=output_pdf,
                data=data
            )
            
            # 4. 에이전트에게 파일이 만들어졌다고 알림
            return f"✅ 서류 생성이 완료되었습니다. 사장님께 현재 작업 폴더에 '{output_pdf}' 파일이 생성되었다고 안내해주세요!"
                
        except json.JSONDecodeError as e:
            return f"❌ 에이전트 JSON 에러: {str(e)}"
        except Exception as e:
            return f"❌ PDF 생성 중 에러가 발생했습니다: {str(e)}"