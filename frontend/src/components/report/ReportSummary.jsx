import { motion } from "motion/react";
import { MessageSquare, Bot, ClipboardList, Calendar } from "lucide-react";

const AGENT_LABEL = {
  admin:    "행정",
  finance:  "재무",
  legal:    "법률·세무",
  location: "상권",
  chat:     "일반",
};

const CARD_ICONS = [MessageSquare, Bot, ClipboardList];

export default function ReportSummary({ totalQueries, mostUsedAgent, checklist, firstActive, lastActive }) {
  const agentLabel = mostUsedAgent?.type
    ? `${AGENT_LABEL[mostUsedAgent.type] ?? mostUsedAgent.type} 에이전트`
    : "-";

  const cards = [
    {
      Icon: CARD_ICONS[0],
      label: "총 질문 수",
      value: totalQueries ?? 0,
      unit: "건",
      sub: null,
      color: "#0891b2",
    },
    {
      Icon: CARD_ICONS[1],
      label: "주요 에이전트",
      value: agentLabel,
      unit: null,
      sub: mostUsedAgent ? `${mostUsedAgent.count}회 사용` : null,
      color: "#10b981",
    },
    {
      Icon: CARD_ICONS[2],
      label: "체크리스트 진행률",
      value: checklist?.total > 0 ? `${checklist.progress_pct ?? 0}%` : "-",
      unit: null,
      sub: checklist?.total > 0 ? `${checklist.completed}/${checklist.total} 항목` : null,
      color: "#8b5cf6",
    },
  ];

  const fmtDate = (iso) => {
    if (!iso) return null;
    return new Date(iso).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short" });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cards.map((card, idx) => {
          const { Icon } = card;
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              whileHover="cardHover"
              variants={{ cardHover: { y: -6 } }}
              className="group"
            >
              <div className="glass rounded-2xl p-6 shadow-elevated transition-glow hover-lift relative overflow-hidden flex flex-col gap-3">
                {/* hover 컬러 오버레이 */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 rounded-2xl"
                  style={{ backgroundColor: card.color }}
                />

                {/* 아이콘 컨테이너 */}
                <motion.div
                  className="w-11 h-11 rounded-xl flex items-center justify-center shadow-lg relative shrink-0"
                  style={{ backgroundColor: `${card.color}20` }}
                  variants={{ cardHover: { rotate: [0, -10, 10, -10, 0] } }}
                  transition={{ duration: 0.5 }}
                >
                  <div
                    className="absolute inset-0 rounded-xl blur-xl opacity-30 group-hover:opacity-50 transition-opacity"
                    style={{ backgroundColor: card.color }}
                  />
                  <Icon size={20} style={{ color: card.color }} className="relative z-10" />
                </motion.div>

                {/* 라벨 */}
                <p className="text-xs font-medium relative z-10" style={{ color: "var(--muted-foreground)" }}>
                  {card.label}
                </p>

                {/* 값 */}
                <div className="relative z-10">
                  <span
                    className="text-2xl font-bold tabular-nums"
                    style={{ color: card.color }}
                  >
                    {card.value}
                  </span>
                  {card.unit && (
                    <span className="text-sm font-normal ml-1" style={{ color: "var(--muted-foreground)" }}>
                      {card.unit}
                    </span>
                  )}
                  {card.sub && (
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                      {card.sub}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* 활동 기간 */}
      {(firstActive || lastActive) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="glass rounded-2xl px-5 py-4 shadow-elevated flex items-center gap-3"
        >
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{ backgroundColor: "rgba(8,145,178,0.12)" }}
          >
            <Calendar size={16} style={{ color: "var(--brand-blue)" }} />
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            {firstActive && (
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                첫 이용 <span style={{ color: "var(--foreground)" }}>{fmtDate(firstActive)}</span>
              </span>
            )}
            {lastActive && (
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                최근 이용 <span style={{ color: "var(--foreground)" }}>{fmtDate(lastActive)}</span>
              </span>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
