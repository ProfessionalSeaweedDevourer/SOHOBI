import ReactMarkdown from "react-markdown";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무" };
const DOMAIN_COLOR = {
  finance: "bg-emerald-100 text-emerald-700",
  admin: "bg-sky-100 text-sky-700",
  legal: "bg-amber-100 text-amber-700",
};

/**
 * @param {{
 *   question: string,
 *   domain?: string,
 *   status?: string,
 *   draft: string,
 *   retryCount?: number,
 *   showMeta?: boolean   // dev 모드에서 true
 * }} props
 */
export default function ResponseCard({ question, domain, status, draft, retryCount, showMeta }) {
  const isEscalated = status === "escalated";

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* 질문 버블 */}
      <div className="self-end max-w-[80%] bg-slate-800 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed">
        {question}
      </div>

      {/* 응답 카드 */}
      <div className="self-start max-w-[90%] w-full">
        {showMeta && domain && (
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${DOMAIN_COLOR[domain] || "bg-slate-100 text-slate-600"}`}>
              {DOMAIN_KR[domain] || domain}
            </span>
            {status && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${isEscalated ? "bg-red-100 text-red-600" : "bg-green-100 text-green-700"}`}>
                {isEscalated ? "escalated" : "approved"}
              </span>
            )}
            {retryCount !== undefined && (
              <span className="text-xs text-slate-400">재시도 {retryCount}회</span>
            )}
          </div>
        )}

        <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm text-sm text-slate-700 prose-response">
          {isEscalated ? (
            <div className="text-amber-700">
              <div className="font-semibold mb-1">검토가 필요합니다</div>
              <div className="text-slate-600 text-xs">이 질문은 에이전트가 최종 검증을 통과하지 못했습니다. 질문을 구체적으로 바꿔 다시 시도해 주세요.</div>
              {draft && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-slate-400">최종 draft 보기</summary>
                  <div className="mt-2 prose-response">
                    <ReactMarkdown>{draft}</ReactMarkdown>
                  </div>
                </details>
              )}
            </div>
          ) : (
            <ReactMarkdown>{draft}</ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}
