/**
 * 사용 리포트 요약 카드 3개
 *
 * @param {object} props
 * @param {number} props.totalQueries    - 총 질문 수
 * @param {object} props.feedback        - {positive, negative, total, positive_rate}
 * @param {object} props.checklist       - {completed, total, progress_pct}
 */
export default function ReportSummary({ totalQueries, feedback, checklist }) {
  const cards = [
    {
      icon: "💬",
      label: "총 질문 수",
      value: totalQueries ?? 0,
      unit: "건",
      color: "#0891b2",
    },
    {
      icon: "👍",
      label: "긍정 피드백",
      value:
        feedback?.positive_rate != null
          ? `${Math.round(feedback.positive_rate * 100)}%`
          : "-",
      sub:
        feedback?.total > 0
          ? `${feedback.positive}/${feedback.total}건`
          : "피드백 없음",
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

  return (
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
  );
}
