const AGENT_LABEL = {
  admin:    "관리",
  finance:  "재무",
  legal:    "법률·세무",
  location: "상권",
  chat:     "일반",
};

/**
 * 사용 리포트 요약 카드 3개
 *
 * @param {object} props
 * @param {number} props.totalQueries      - 총 질문 수
 * @param {object} [props.mostUsedAgent]   - {type, count} 가장 많이 사용한 에이전트
 * @param {object} props.feedback          - {positive, negative, total, positive_rate, top_negative_tags}
 * @param {object} props.checklist         - {completed, total, progress_pct}
 * @param {string} [props.firstActive]     - 최초 활동 시각 (ISO 8601)
 * @param {string} [props.lastActive]      - 최근 활동 시각 (ISO 8601)
 */
export default function ReportSummary({ totalQueries, mostUsedAgent, feedback, checklist, firstActive, lastActive }) {
  const agentLabel = mostUsedAgent?.type
    ? `${AGENT_LABEL[mostUsedAgent.type] ?? mostUsedAgent.type} 에이전트`
    : "-";

  const cards = [
    {
      icon: "💬",
      label: "총 질문 수",
      value: totalQueries ?? 0,
      unit: "건",
      color: "#0891b2",
    },
    {
      icon: "🤖",
      label: "주요 에이전트",
      value: agentLabel,
      sub: mostUsedAgent ? `${mostUsedAgent.count}회 사용` : "",
      color: "#10b981",
    },
    {
      icon: "📋",
      label: "체크리스트 진행률",
      value:
        checklist?.total > 0
          ? `${checklist.progress_pct ?? 0}%`
          : "-",
      sub:
        checklist?.total > 0
          ? `${checklist.completed}/${checklist.total}항목`
          : "",
      color: "#8b5cf6",
    },
  ];

  const fmtDate = (iso) => {
    if (!iso) return null;
    return new Date(iso).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short" });
  };

  return (
    <div className="flex flex-col gap-3">
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-2xl border p-4 flex flex-col gap-1"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
            boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
          }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xl">{card.icon}</span>
            <span
              className="text-xs font-medium"
              style={{ color: "var(--muted-foreground)" }}
            >
              {card.label}
            </span>
          </div>
          <div
            className="text-2xl font-bold tabular-nums mt-1"
            style={{ color: card.color }}
          >
            {card.value}
            {card.unit && (
              <span className="text-sm font-normal ml-1" style={{ color: "var(--muted-foreground)" }}>
                {card.unit}
              </span>
            )}
          </div>
          {card.sub && (
            <div className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {card.sub}
            </div>
          )}
        </div>
      ))}
    </div>
    {(firstActive || lastActive) && (
      <div className="text-xs flex gap-4" style={{ color: "var(--muted-foreground)" }}>
        {firstActive && <span>첫 이용: {fmtDate(firstActive)}</span>}
        {lastActive && <span>최근 이용: {fmtDate(lastActive)}</span>}
      </div>
    )}
    </div>
  );
}
