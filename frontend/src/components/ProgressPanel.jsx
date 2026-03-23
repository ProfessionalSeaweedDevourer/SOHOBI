/**
 * ProgressPanel: SSE 이벤트를 실시간으로 받아 진행 타임라인을 표시한다.
 *
 * events 배열 형식:
 *   { event: "domain_classified", domain, session_id }
 *   { event: "agent_start", attempt, max_attempts }
 *   { event: "agent_done", attempt, agent_ms }
 *   { event: "signoff_start", attempt }
 *   { event: "signoff_result", attempt, approved, grade, issues, warnings, retry_prompt, signoff_ms }
 *   { event: "complete", status, grade, ... }
 *   { event: "error", message }
 */

const DOMAIN_LABEL = {
  admin:    "행정·신고",
  finance:  "재무·시뮬레이션",
  legal:    "법률·세무",
  location: "상권 분석",
};

const GRADE_COLOR = {
  A: "text-green-700",
  B: "text-amber-600",
  C: "text-red-600",
};

const ITEM_LABELS = {
  C1: "질문 응답성", C2: "완결성", C3: "내부 일관성", C4: "톤 적절성", C5: "할루시네이션",
  F1: "수치 제시", F2: "단위 표기", F3: "가정 전제", F4: "불확실성", F5: "리스크 경고",
  G1: "근거 출처", G2: "법령 인용", G3: "조문 번호", G4: "면책 고지",
  A1: "지역 정보", A2: "업종 정보", A3: "수치 근거", A4: "기간 명시", A5: "출처 안내",
  S1: "상권 범위", S2: "매출 데이터", S3: "유동인구", S4: "경쟁 현황", S5: "입지 평가",
};

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
  );
}

function CodeBadge({ code, type }) {
  const color =
    type === "passed"   ? "bg-green-100 text-green-700" :
    type === "warning"  ? "bg-amber-100 text-amber-700" :
                          "bg-red-100 text-red-600";
  return (
    <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${color}`}>
      {code}
    </span>
  );
}

/**
 * @param {{ events: Array<object>, detailed?: boolean }} props
 *   detailed=true  → 개발자 모드: 이슈 코드·이유·수정 지시 전부 표시
 *   detailed=false → 사용자 모드: 단계 이름과 스피너만 표시
 */
export default function ProgressPanel({ events = [], detailed = false }) {
  if (events.length === 0) return null;

  // 이벤트를 도메인 분류 + 시도별 그룹으로 재구성
  const domain = events.find(e => e.event === "domain_classified")?.domain;
  const error  = events.find(e => e.event === "error");

  // attempt별 이벤트 묶음
  const attemptMap = {};
  for (const ev of events) {
    if (!ev.attempt) continue;
    if (!attemptMap[ev.attempt]) attemptMap[ev.attempt] = {};
    attemptMap[ev.attempt][ev.event] = ev;
  }
  const attempts = Object.entries(attemptMap).sort(([a], [b]) => Number(a) - Number(b));
  const maxAttempts = events.find(e => e.event === "agent_start")?.max_attempts ?? "?";

  const isComplete = events.some(e => e.event === "complete");

  return (
    <div className="text-xs text-slate-600 space-y-1.5 py-1">
      {/* 도메인 */}
      {domain && (
        <div className="flex items-center gap-1.5 text-slate-500">
          <span className="text-slate-400">도메인</span>
          <span className="font-medium text-slate-700">
            {DOMAIN_LABEL[domain] || domain}
          </span>
        </div>
      )}

      {/* 시도별 타임라인 */}
      {attempts.map(([attemptNum, evs]) => {
        const agentStart   = evs["agent_start"];
        const agentDone    = evs["agent_done"];
        const signoffStart = evs["signoff_start"];
        const signoffResult= evs["signoff_result"];

        return (
          <div key={attemptNum} className="border-l-2 border-slate-200 pl-3 space-y-1">
            <div className="text-slate-400 font-medium">
              시도 {attemptNum} / {maxAttempts}
            </div>

            {/* 에이전트 */}
            <div className="flex items-center gap-1.5">
              {agentDone
                ? <span className="text-green-600">✓</span>
                : <Spinner />}
              <span>
                {agentDone
                  ? `에이전트 완료 (${(agentDone.agent_ms / 1000).toFixed(1)}초)`
                  : "에이전트 작업 중…"}
              </span>
            </div>

            {/* Sign-off */}
            {(signoffStart || signoffResult) && (
              <div className="flex items-center gap-1.5">
                {signoffResult
                  ? (signoffResult.approved
                      ? <span className="text-green-600">✓</span>
                      : <span className="text-red-500">✗</span>)
                  : <Spinner />}
                <span>
                  {signoffResult
                    ? (signoffResult.approved
                        ? `검증 통과 (${GRADE_COLOR[signoffResult.grade] ? signoffResult.grade + "등급" : ""})`
                        : `반려 (${signoffResult.grade}등급)`)
                    : "검증 중…"}
                </span>
                {signoffResult && (
                  <span className={`font-semibold ${GRADE_COLOR[signoffResult.grade] || ""}`}>
                    {signoffResult.grade}
                  </span>
                )}
              </div>
            )}

            {/* 상세: 반려 이유 (detailed 모드만) */}
            {detailed && signoffResult && !signoffResult.approved && (
              <div className="ml-4 space-y-1 mt-1">
                {/* 코드 배지 */}
                <div className="flex flex-wrap gap-1">
                  {(signoffResult.passed || []).map(c => <CodeBadge key={c} code={c} type="passed" />)}
                  {(signoffResult.warnings || []).map(w => <CodeBadge key={w.code} code={w.code} type="warning" />)}
                  {(signoffResult.issues || []).map(i => <CodeBadge key={i.code} code={i.code} type="issue" />)}
                </div>
                {/* 이슈 이유 */}
                {(signoffResult.issues || []).map(i => (
                  <div key={i.code} className="bg-red-50 border border-red-100 rounded px-2 py-1">
                    <span className="font-semibold text-red-700">{i.code}</span>
                    <span className="text-red-500"> — {ITEM_LABELS[i.code] || i.code}</span>
                    {i.reason && <div className="text-slate-500 mt-0.5">{i.reason}</div>}
                  </div>
                ))}
                {/* 수정 지시문 */}
                {signoffResult.retry_prompt && (
                  <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1">
                    <div className="text-slate-400 mb-0.5">수정 지시</div>
                    <div className="text-slate-600 whitespace-pre-wrap leading-relaxed">
                      {signoffResult.retry_prompt}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* 완료 표시 */}
      {isComplete && (
        <div className="text-slate-400 pt-0.5">완료</div>
      )}

      {/* 오류 */}
      {error && (
        <div className="text-red-600 bg-red-50 rounded px-2 py-1">
          오류: {error.message}
        </div>
      )}
    </div>
  );
}
