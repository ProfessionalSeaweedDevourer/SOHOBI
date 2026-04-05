/**
 * 소상공인 창업 준비 체크리스트 항목 정의
 * autoCheckKeywords: 에이전트 응답 draft에서 자동 매칭할 한글 키워드
 * (백엔드 checklist_store.py의 CHECKLIST_KEYWORDS와 동기화)
 */
export const CHECKLIST_ITEMS = [
  {
    id: "biz_type",
    label: "업종 결정",
    description: "창업할 업종·업태 확정",
    icon: "🏪",
    autoCheckKeywords: ["업종", "업태", "일반음식점", "휴게음식점", "제과제빵", "소매업"],
  },
  {
    id: "location",
    label: "입지 선정",
    description: "상권 분석 및 매장 위치 확정",
    icon: "📍",
    autoCheckKeywords: ["상권", "입지", "유동인구", "상가", "동네", "매장 위치"],
  },
  {
    id: "capital",
    label: "초기 자금 계획",
    description: "창업 비용 및 자금 조달 수립",
    icon: "💰",
    autoCheckKeywords: ["초기 자금", "창업 비용", "자본금", "투자금", "대출", "손익분기"],
  },
  {
    id: "biz_reg",
    label: "사업자 등록",
    description: "사업자 등록증 발급 및 세무 신고",
    icon: "📄",
    autoCheckKeywords: ["사업자등록", "사업자 등록", "세무서", "개인사업자", "법인"],
  },
  {
    id: "permit",
    label: "영업 허가·신고",
    description: "식품위생법 영업신고 또는 인허가 완료",
    icon: "✅",
    autoCheckKeywords: ["영업신고", "영업 신고", "위생교육", "허가", "인허가", "식품위생"],
  },
  {
    id: "labor",
    label: "인력 채용 계획",
    description: "직원 채용 및 4대보험 처리",
    icon: "👤",
    autoCheckKeywords: ["직원", "아르바이트", "알바", "4대보험", "근로계약", "인건비"],
  },
  {
    id: "finance_sim",
    label: "수익성 검토",
    description: "손익 시뮬레이션 및 BEP 분석",
    icon: "📊",
    autoCheckKeywords: ["수익성", "손익", "매출", "순이익", "재료비", "시뮬레이션", "BEP"],
  },
  {
    id: "lease",
    label: "임대차 계약",
    description: "임대차 계약서 검토 및 체결",
    icon: "🤝",
    autoCheckKeywords: ["임대차", "임대 계약", "권리금", "보증금", "월세", "임차인"],
  },
];

export const CHECKLIST_ITEM_IDS = CHECKLIST_ITEMS.map((item) => item.id);
