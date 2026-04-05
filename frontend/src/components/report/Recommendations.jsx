import { CHECKLIST_ITEMS } from "../../constants/checklistItems";

const AGENT_FOR_ITEM = {
  biz_type:    { label: "업종 상담", path: "/user", hint: "AI 에이전트에게 업종·업태 결정을 물어보세요" },
  location:    { label: "상권 분석", path: "/map",  hint: "상권 지도에서 입지를 분석해 보세요" },
  capital:     { label: "자금 계획",  path: "/user", hint: "재무 에이전트로 초기 자금 계획을 세워보세요" },
  biz_reg:     { label: "사업자 등록", path: "/user", hint: "법률 에이전트에게 사업자 등록 절차를 확인하세요" },
  permit:      { label: "영업 신고",  path: "/user", hint: "행정 에이전트에게 영업 허가·신고를 문의하세요" },
  labor:       { label: "인력 채용",  path: "/user", hint: "법률 에이전트에게 근로계약·4대보험을 확인하세요" },
  finance_sim: { label: "수익성 검토", path: "/user", hint: "재무 에이전트로 손익 시뮬레이션을 실행해 보세요" },
  lease:       { label: "임대차 계약", path: "/user", hint: "법률 에이전트에게 임대차 계약서 검토를 요청하세요" },
};

/**
 * 미완료 체크리스트 항목 기반 다음 할 일 추천
 *
 * @param {object}   props
 * @param {string[]} props.incompleteItems - 미완료 item_id 배열
 */
export default function Recommendations({ incompleteItems }) {
  if (!incompleteItems?.length) {
    return (
      <div
        className="rounded-2xl border p-4 text-center"
        style={{
          background: "var(--card)",
          borderColor: "var(--border)",
          boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
        }}
      >
        <div className="text-2xl mb-2">🎉</div>
        <div className="text-sm font-semibold" style={{ color: "#10b981" }}>
          모든 준비가 완료되었습니다!
        </div>
      </div>
    );
  }

  const items = incompleteItems
    .slice(0, 3)
    .map((id) => {
      const def = CHECKLIST_ITEMS.find((c) => c.id === id);
      const rec = AGENT_FOR_ITEM[id];
      return { id, icon: def?.icon ?? "📌", label: def?.label ?? id, ...rec };
    });

  return (
    <div
      className="rounded-2xl border p-4"
      style={{
        background: "var(--card)",
        borderColor: "var(--border)",
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
      }}
    >
      <div className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
        다음 단계 추천
      </div>
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <a
            key={item.id}
            href={item.path}
            className="flex items-start gap-3 rounded-xl p-3 transition-colors hover:opacity-80"
            style={{ background: "var(--muted)", textDecoration: "none" }}
          >
            <span className="text-xl mt-0.5">{item.icon}</span>
            <div>
              <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                {item.label}
              </div>
              <div className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                {item.hint}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
