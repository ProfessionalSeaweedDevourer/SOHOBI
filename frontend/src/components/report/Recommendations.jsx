import { motion } from "motion/react";
import { ArrowRight, Sparkles } from "lucide-react";
import { CHECKLIST_ITEMS } from "../../constants/checklistItems";
import { trackEvent } from "../../utils/trackEvent";

const AGENT_FOR_ITEM = {
  biz_type:    { label: "업종 상담",   path: "/user", hint: "AI 에이전트에게 업종·업태 결정을 물어보세요",        color: "#0891b2" },
  location:    { label: "상권 분석",   path: "/map",  hint: "상권 지도에서 입지를 분석해 보세요",                color: "#14b8a6" },
  capital:     { label: "자금 계획",   path: "/user", hint: "재무 에이전트로 초기 자금 계획을 세워보세요",        color: "#f97316" },
  biz_reg:     { label: "사업자 등록", path: "/user", hint: "법률 에이전트에게 사업자 등록 절차를 확인하세요",    color: "#8b5cf6" },
  permit:      { label: "영업 신고",   path: "/user", hint: "행정 에이전트에게 영업 허가·신고를 문의하세요",      color: "#0891b2" },
  labor:       { label: "인력 채용",   path: "/user", hint: "법률 에이전트에게 근로계약·4대보험을 확인하세요",    color: "#ec4899" },
  finance_sim: { label: "수익성 검토", path: "/user", hint: "재무 에이전트로 손익 시뮬레이션을 실행해 보세요",    color: "#f97316" },
  lease:       { label: "임대차 계약", path: "/user", hint: "법률 에이전트에게 임대차 계약서 검토를 요청하세요",  color: "#8b5cf6" },
};

export default function Recommendations({ incompleteItems, sessionId }) {
  if (!incompleteItems?.length) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="glass rounded-2xl p-6 shadow-elevated text-center relative overflow-hidden"
      >
        <div className="absolute inset-0 opacity-5 rounded-2xl" style={{ backgroundColor: "#10b981" }} />
        <div className="relative z-10">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg"
               style={{ backgroundColor: "rgba(16,185,129,0.15)" }}>
            <span className="text-2xl">🎉</span>
          </div>
          <div className="font-semibold gradient-text text-lg">모든 준비가 완료되었습니다!</div>
          <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
            창업 체크리스트를 모두 완료했어요
          </p>
        </div>
      </motion.div>
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
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="glass rounded-2xl shadow-elevated overflow-hidden"
    >
      {/* 섹션 헤더 */}
      <div className="px-5 pt-5 pb-4 flex items-center gap-2 border-b" style={{ borderColor: "var(--border)" }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: "rgba(249,115,22,0.12)" }}
        >
          <Sparkles size={15} style={{ color: "#f97316" }} />
        </div>
        <span className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
          이런 준비가 남아있어요
        </span>
      </div>

      <div className="px-5 pb-5 pt-4 flex flex-col gap-3">
        {items.map((item, idx) => (
          <motion.a
            key={item.id}
            href={item.path}
            initial={{ opacity: 0, x: -10 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: idx * 0.08 }}
            whileHover={{ x: 4 }}
            className="group flex items-center gap-3 rounded-xl p-3.5 transition-colors"
            style={{ background: "var(--muted)", textDecoration: "none" }}
            onClick={() => trackEvent("report_recommendation_click", {
              session_id: sessionId,
              item_id: item.id,
              agent: item.path,
            })}
          >
            {/* 아이콘 컨테이너 */}
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-lg transition-transform group-hover:scale-110"
              style={{ backgroundColor: item.color ? `${item.color}18` : "var(--card)" }}
            >
              {item.icon}
            </div>

            {/* 텍스트 */}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                {item.label}
              </div>
              <div className="text-xs mt-0.5 truncate" style={{ color: "var(--muted-foreground)" }}>
                {item.hint}
              </div>
            </div>

            {/* 화살표 */}
            <ArrowRight
              size={16}
              className="shrink-0 opacity-40 group-hover:opacity-80 transition-opacity"
              style={{ color: item.color ?? "var(--foreground)" }}
            />
          </motion.a>
        ))}
      </div>
    </motion.div>
  );
}
