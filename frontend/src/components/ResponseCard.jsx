import ReactMarkdown from "react-markdown";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무", location: "상권분석" };
const DOMAIN_COLOR = {
  finance: "bg-emerald-100 text-emerald-700",
  admin: "bg-sky-100 text-sky-700",
  legal: "bg-amber-100 text-amber-700",
  location: "bg-violet-100 text-violet-700",
};

const GRADE_STYLE = {
  A: "bg-green-100 text-green-700",
  B: "bg-amber-100 text-amber-700",
  C: "bg-red-100 text-red-600",
};
const GRADE_LABEL = {
  A: "A 통과",
  B: "B 경고",
  C: "C 반려",
};

/**
 * @param {{
 *   question: string,
 *   domain?: string,
 *   status?: string,
 *   grade?: string,          // "A" | "B" | "C"
 *   confidenceNote?: string, // grade B 시 경고 요약
 *   draft: string,
 *   retryCount?: number,
 *   showMeta?: boolean        // dev 모드에서 true
 * }} props
 */
export default function ResponseCard({ question, domain, status, grade, confidenceNote, draft, retryCount, chart, showMeta }) {
  const isEscalated = status === "escalated";
  // grade가 없을 때는 status로 추론
  const effectiveGrade = grade || (isEscalated ? "C" : "A");

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* 질문 버블 */}
      <div className="self-end max-w-[80%] bg-slate-800 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed">
        {question}
      </div>

      {/* 응답 카드 */}
      <div className="self-start max-w-[90%] w-full">
        {showMeta && domain && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${DOMAIN_COLOR[domain] || "bg-slate-100 text-slate-600"}`}>
              {DOMAIN_KR[domain] || domain}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${GRADE_STYLE[effectiveGrade] || "bg-slate-100 text-slate-600"}`}>
              {GRADE_LABEL[effectiveGrade] || effectiveGrade}
            </span>
            {retryCount !== undefined && retryCount > 0 && (
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
          <div className="mt-2 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 text-xs text-amber-700">
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
