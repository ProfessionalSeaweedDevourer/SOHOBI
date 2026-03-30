import { motion } from "motion/react";
import { CheckCircle2, XCircle } from "lucide-react";
import { LoadingDots } from "./LoadingSpinner";

const DOMAIN_LABEL = {
  admin:    "행정·신고",
  finance:  "재무·시뮬레이션",
  legal:    "법률·세무",
  location: "상권 분석",
};

const GRADE_COLOR = {
  A: "var(--grade-a)",
  B: "var(--grade-b)",
  C: "var(--grade-c)",
};

const ITEM_LABELS = {
  C1: "질문 응답성", C2: "완결성", C3: "내부 일관성", C4: "톤 적절성", C5: "할루시네이션",
  F1: "수치 제시", F2: "단위 표기", F3: "가정 전제", F4: "불확실성", F5: "리스크 경고",
  G1: "근거 출처", G2: "법령 인용", G3: "조문 번호", G4: "면책 고지",
  A1: "지역 정보", A2: "업종 정보", A3: "수치 근거", A4: "기간 명시", A5: "출처 안내",
  S1: "상권 범위", S2: "매출 데이터", S3: "유동인구", S4: "경쟁 현황", S5: "입지 평가",
};

function CodeBadge({ code, type }) {
  const styleMap = {
    passed:  { background: "rgba(16,185,129,0.15)", color: "var(--grade-a)" },
    warning: { background: "rgba(234,179,8,0.15)",  color: "var(--grade-b)" },
    issue:   { background: "rgba(239,68,68,0.15)",  color: "var(--grade-c)" },
  };
  return (
    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={styleMap[type] || styleMap.issue}>
      {code}
    </span>
  );
}

export default function ProgressPanel({ events = [], detailed = false }) {
  if (events.length === 0) return null;

  const domain = events.find(e => e.event === "domain_classified")?.domain;
  const error  = events.find(e => e.event === "error");

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
    <div className="text-xs text-foreground space-y-1.5 py-1">
      {domain && (
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-1.5 text-muted-foreground"
        >
          <span className="opacity-60">도메인</span>
          <span className="font-medium text-foreground">{DOMAIN_LABEL[domain] || domain}</span>
        </motion.div>
      )}

      {attempts.map(([attemptNum, evs], idx) => {
        const agentDone    = evs["agent_done"];
        const signoffStart = evs["signoff_start"];
        const signoffResult= evs["signoff_result"];

        return (
          <motion.div
            key={attemptNum}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="border-l-2 border-[var(--border)] pl-3 space-y-1"
          >
            <div className="text-muted-foreground font-medium">
              시도 {attemptNum} / {maxAttempts}
            </div>

            <div className="flex items-center gap-1.5">
              {agentDone
                ? <CheckCircle2 size={12} style={{ color: "var(--grade-a)" }} />
                : <LoadingDots />}
              <span>
                {agentDone
                  ? `에이전트 완료 (${(agentDone.agent_ms / 1000).toFixed(1)}초)`
                  : "에이전트 작업 중…"}
              </span>
            </div>

            {(signoffStart || signoffResult) && (
              <div className="flex items-center gap-1.5">
                {signoffResult
                  ? (signoffResult.approved
                      ? <CheckCircle2 size={12} style={{ color: "var(--grade-a)" }} />
                      : <XCircle size={12} style={{ color: "var(--grade-c)" }} />)
                  : <LoadingDots />}
                <span>
                  {signoffResult
                    ? (signoffResult.approved
                        ? `검증 통과`
                        : `반려`)
                    : "검증 중…"}
                </span>
                {signoffResult && (
                  <span className="font-semibold" style={{ color: GRADE_COLOR[signoffResult.grade] }}>
                    {signoffResult.grade}
                  </span>
                )}
              </div>
            )}

            {detailed && signoffResult && !signoffResult.approved && (
              <div className="ml-4 space-y-1 mt-1">
                <div className="flex flex-wrap gap-1">
                  {(signoffResult.passed   || []).map(c => <CodeBadge key={c}      code={c}       type="passed"  />)}
                  {(signoffResult.warnings || []).map(w => <CodeBadge key={w.code} code={w.code}  type="warning" />)}
                  {(signoffResult.issues   || []).map(i => <CodeBadge key={i.code} code={i.code}  type="issue"   />)}
                </div>
                {(signoffResult.issues || []).map(i => (
                  <div key={i.code} className="rounded px-2 py-1 border" style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.2)" }}>
                    <span className="font-semibold" style={{ color: "var(--grade-c)" }}>{i.code}</span>
                    <span style={{ color: "var(--grade-c)", opacity: 0.7 }}> — {ITEM_LABELS[i.code] || i.code}</span>
                    {i.reason && <div className="text-muted-foreground mt-0.5">{i.reason}</div>}
                  </div>
                ))}
                {signoffResult.retry_prompt && (
                  <div className="glass rounded px-2 py-1">
                    <div className="text-muted-foreground mb-0.5">수정 지시</div>
                    <div className="text-foreground opacity-80 whitespace-pre-wrap leading-relaxed">
                      {signoffResult.retry_prompt}
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        );
      })}

      {isComplete && (
        <div className="text-muted-foreground pt-0.5">완료</div>
      )}

      {error && (
        <div className="rounded px-2 py-1 border" style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.2)", color: "var(--grade-c)" }}>
          오류: {error.message}
        </div>
      )}
    </div>
  );
}
