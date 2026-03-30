import ReactMarkdown from "react-markdown";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무", location: "상권분석" };
const DOMAIN_COLOR = {
  finance: { background: "rgba(20,184,166,0.15)", color: "var(--brand-teal)" },
  admin:   { background: "rgba(8,145,178,0.15)",  color: "var(--brand-blue)" },
  legal:   { background: "rgba(249,115,22,0.15)", color: "var(--brand-orange)" },
  location:{ background: "rgba(20,184,166,0.15)", color: "var(--brand-teal)" },
};

const GRADE_STYLE = {
  A: { background: "rgba(16,185,129,0.15)", color: "var(--grade-a)" },
  B: { background: "rgba(234,179,8,0.15)",  color: "var(--grade-b)" },
  C: { background: "rgba(239,68,68,0.15)",  color: "var(--grade-c)" },
};
const GRADE_LABEL = { A: "A 통과", B: "B 경고", C: "C 반려" };

export default function ResponseCard({ question, domain, status, grade, confidenceNote, draft, retryCount, chart, showMeta }) {
  const isEscalated = status === "escalated";
  const effectiveGrade = grade || (isEscalated ? "C" : "A");

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* 질문 버블 */}
      <div
        className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed"
        style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
      >
        {question}
      </div>

      {/* 응답 카드 */}
      <div className="self-start max-w-[90%] w-full">
        {showMeta && domain && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span
              className="text-xs font-semibold px-2 py-0.5 rounded-full"
              style={DOMAIN_COLOR[domain] || { background: "var(--muted)", color: "var(--muted-foreground)" }}
            >
              {DOMAIN_KR[domain] || domain}
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full font-semibold"
              style={GRADE_STYLE[effectiveGrade] || { background: "var(--muted)", color: "var(--muted-foreground)" }}
            >
              {GRADE_LABEL[effectiveGrade] || effectiveGrade}
            </span>
            {retryCount !== undefined && retryCount > 0 && (
              <span className="text-xs text-muted-foreground">재시도 {retryCount}회</span>
            )}
          </div>
        )}

        <div className="glass rounded-2xl rounded-tl-sm px-5 py-4 shadow-elevated text-sm text-foreground prose-response">
          {isEscalated ? (
            <div style={{ color: "var(--grade-b)" }}>
              <div className="font-semibold mb-1">검토가 필요합니다</div>
              <div className="text-muted-foreground text-xs">이 질문은 에이전트가 최종 검증을 통과하지 못했습니다. 질문을 구체적으로 바꿔 다시 시도해 주세요.</div>
              {draft && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-muted-foreground">최종 draft 보기</summary>
                  <div className="mt-2 prose-response">
                    <ReactMarkdown>{draft}</ReactMarkdown>
                  </div>
                </details>
              )}
            </div>
          ) : (
            <>
              <ReactMarkdown>{draft}</ReactMarkdown>
              {chart && (
                <div className="mt-3">
                  <img
                    src={`data:image/png;base64,${chart}`}
                    alt="시뮬레이션 결과 그래프"
                    className="rounded-lg max-w-full"
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* 사용자 모드: grade B일 때 주의 배너 */}
        {!showMeta && effectiveGrade === "B" && (
          <div
            className="mt-2 flex items-start gap-2 rounded-xl px-3 py-2 text-xs border"
            style={{
              background: "rgba(234,179,8,0.1)",
              borderColor: "rgba(234,179,8,0.3)",
              color: "var(--grade-b)",
            }}
          >
            <span className="mt-0.5">⚠</span>
            <span>
              {confidenceNote
                ? confidenceNote
                : "일부 주의 사항이 포함된 응답입니다. 중요한 결정 전에 전문가 상담을 권장합니다."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
