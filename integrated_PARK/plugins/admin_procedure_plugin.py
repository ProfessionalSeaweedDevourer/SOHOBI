"""
행정 절차 Knowledge Base 플러그인
- 데이터 소스: integrated_PARK/data/admin_procedures.json (법령 검증된 절차 정보)
- 목적: LLM 일반 지식 의존 제거 → 구조화된 절차 정보 직접 제공
- 법령 근거: CHOI/vectorSearch/refined_law_data_1.json 기준 검증 완료
"""

import json
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function

_DATA_FILE = Path(__file__).parent.parent / "data" / "admin_procedures.json"

KEYWORD_MAP: dict[str, str] = {
    "영업신고": "food_biz_report",
    "일반음식점": "food_biz_report",
    "휴게음식점": "food_biz_report",
    "식품영업": "food_biz_report",
    "위생교육": "hygiene_education",
    "위생 교육": "hygiene_education",
    "사업자등록": "business_registration",
    "보건증": "health_certificate",
    "건강진단": "health_certificate",
    "소방": "fire_safety",
    "완비증명": "fire_safety",
    "안전시설": "fire_safety",
}


class AdminProcedurePlugin:
    """
    행정 절차 Knowledge Base 플러그인.
    법령 검증된 JSON 데이터를 키워드 매칭으로 조회하여 구조화된 절차 정보를 반환한다.
    """

    def __init__(self):
        with open(_DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        self._index: dict[str, dict] = {p["id"]: p for p in data["procedures"]}

    @kernel_function(
        name="get_admin_procedure",
        description=(
            "외식업 창업 행정 절차(영업신고·위생교육·사업자등록·보건증·소방완비증명) 정보를 "
            "법령 검증된 Knowledge Base에서 조회합니다. "
            "필요 서류·담당기관·처리기한·법령 근거(조항 번호 포함)를 구조화된 형태로 반환합니다."
        ),
    )
    def get_admin_procedure(
        self,
        query: Annotated[
            str,
            "절차 유형 키워드 (예: 영업신고, 위생교육, 사업자등록, 보건증, 소방)",
        ],
    ) -> str:
        matched_id: str | None = None
        for kw, proc_id in KEYWORD_MAP.items():
            if kw in query:
                matched_id = proc_id
                break

        if not matched_id:
            available = "영업신고, 위생교육, 사업자등록, 보건증, 소방완비증명"
            return (
                f"[AdminProcedureKB] '{query}'에 해당하는 절차 정보를 찾지 못했습니다.\n"
                f"조회 가능한 절차: {available}"
            )

        proc = self._index[matched_id]
        steps_text = "\n".join(proc["steps"])
        docs_text = "\n".join(f"  - {d}" for d in proc["required_docs"])

        return (
            f"[AdminProcedureKB — {proc['name']}]\n"
            f"법령 근거: {proc['law']}\n"
            f"신고 서식: {proc['form']}\n"
            f"관할 기관: {proc['authority']}\n"
            f"온라인 신청: {proc['online']}\n"
            f"\n절차:\n{steps_text}\n"
            f"\n필요 서류:\n{docs_text}\n"
            f"\n처리 기한: {proc['deadline']}\n"
            f"수수료: {proc['fee']}"
        )
