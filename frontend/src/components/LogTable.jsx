import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { GradeBadge } from "./GradeBadge";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무", location: "상권분석" };
const DOMAIN_STYLE = {
  finance: { background: "rgba(16,185,129,0.12)", color: "var(--grade-a, #10b981)" },
  admin: { background: "rgba(8,145,178,0.12)", color: "var(--brand-blue)" },
  legal: { background: "rgba(245,158,11,0.12)", color: "var(--grade-b, #f59e0b)" },
  location: { background: "rgba(139,92,246,0.12)", color: "#8b5cf6" },
};
const ITEM_LABELS = {
  C1: "질문 응답성", C2: "완결성", C3: "내부 일관성", C4: "톤 적절성", C5: "할루시네이션 징후",
  F1: "수치 제시", F2: "단위 표기", F3: "가정 전제", F4: "불확실성", F5: "리스크 경고",
  G1: "근거 출처", G2: "법령 인용", G3: "조문 번호", G4: "면책 고지",
  A1: "지역 정보", A2: "업종 정보", A3: "수치 근거", A4: "기간 명시", A5: "출처 안내",
  S1: "수치 제시", S2: "데이터 기준", S3: "기회·리스크", S4: "지역·업종 명시", S5: "정보 제공 면책",
};

function resolveGrade(entry) {
  if (entry.grade && ["A", "B", "C"].includes(entry.grade)) return entry.grade;
  return entry.status === "approved" ? "A" : "C";
}

function fmtTs(ts) {
  if (!ts) return "-";
  try {
    const normalized = ts.replace(/(\.\d{3})\d+/, "$1");
    return new Date(normalized).toLocaleString("ko-KR", {
      month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function DomainBadge({ domain }) {
  const style = DOMAIN_STYLE[domain] || { background: "var(--accent)", color: "var(--muted-foreground)" };
  return (
    <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold" style={style}>
      {DOMAIN_KR[domain] || domain}
    </span>
  );
}

/**
 * @param {{ entries: Array, loading: boolean }} props
 */
export default function LogTable({ entries, loading }) {
  const [selected, setSelected] = useState(null);

  if (loading) {
    return <div className="text-center py-20 text-muted-foreground text-sm">로그 불러오는 중…</div>;
  }
  if (!entries || entries.length === 0) {
    return <div className="text-center py-20 text-muted-foreground text-sm">로그가 없습니다.</div>;
  }

  return (
    <div className="flex gap-4 h-full">
      {/* 목록 */}
      <div className="w-full lg:w-1/2 overflow-y-auto flex flex-col gap-1.5 pr-1">
        {entries.map((entry, i) => {
          const grade = resolveGrade(entry);
          const isSelected = selected === i;
          return (
            <button
              key={i}
              onClick={() => setSelected(isSelected ? null : i)}
              className={`
                w-full text-left text-xs border rounded-xl px-3 py-2.5 transition-all
                ${isSelected
                  ? "border-[var(--brand-teal)] bg-[rgba(20,184,166,0.08)]"
                  : "border-[var(--border)] glass hover:bg-white/10"}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <GradeBadge grade={grade} size="sm" />
                <DomainBadge domain={entry.domain} />
                <span className="text-muted-foreground">{fmtTs(entry.ts)}</span>
                <span className="ml-auto text-muted-foreground">{(entry.latency_ms || 0).toFixed(0)}ms</span>
              </div>
              <div className="text-foreground truncate">{entry.question}</div>
              {entry.retry_count > 0 && (
                <div className="text-muted-foreground mt-0.5">재시도 {entry.retry_count}회</div>
              )}
            </button>
          );
        })}
      </div>

      {/* 상세 패널 */}
      <div className="hidden lg:flex lg:w-1/2 flex-col border border-[var(--border)] rounded-xl glass overflow-y-auto">
        {selected === null ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            항목을 선택하면 상세 내용이 표시됩니다.
          </div>
        ) : (
          <EntryDetail entry={entries[selected]} />
        )}
      </div>

      {/* 모바일: 선택 항목 상세 (모달 느낌) */}
      {selected !== null && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/30 flex items-end">
          <div className="glass-card w-full rounded-t-2xl max-h-[80vh] overflow-y-auto p-4">
            <button
              onClick={() => setSelected(null)}
              className="mb-3 text-sm text-muted-foreground"
            >
              ✕ 닫기
            </button>
            <EntryDetail entry={entries[selected]} />
          </div>
        </div>
      )}
    </div>
  );
}

function EntryDetail({ entry }) {
  const rejHist = entry.rejection_history || [];
  const [openIdx, setOpenIdx] = useState(null);
  const grade = resolveGrade(entry);

  return (
    <div className="p-4 text-xs space-y-4">
      {/* 메타 */}
      <div className="flex flex-wrap gap-2 items-center">
        <GradeBadge grade={grade} size="sm" />
        <DomainBadge domain={entry.domain} />
        <span className="text-muted-foreground">{fmtTs(entry.ts)}</span>
        <span className="text-muted-foreground">{(entry.latency_ms || 0).toFixed(0)}ms</span>
        <span className="text-muted-foreground">재시도 {entry.retry_count}회</span>
        {entry.status === "escalated" && (
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(245,158,11,0.12)", color: "var(--grade-b)" }}>에스컬레이션</span>
        )}
      </div>

      {/* confidence_note */}
      {entry.confidence_note && (
        <div className="rounded-lg px-3 py-2" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", color: "var(--foreground)" }}>
          <span className="font-semibold">주의: </span>{entry.confidence_note}
        </div>
      )}

      {/* 질문 */}
      <div>
        <div className="font-semibold text-muted-foreground mb-1">질문</div>
        <div className="text-foreground leading-relaxed">{entry.question}</div>
      </div>

      {/* 거부 이력 */}
      {rejHist.length > 0 && (
        <div>
          <div className="font-semibold text-muted-foreground mb-2">거부 이력</div>
          <div className="space-y-2">
            {rejHist.map((a, i) => (
              <div key={i} className="border border-[var(--border)] rounded-lg overflow-hidden">
                <button
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="w-full flex items-center gap-2 px-3 py-2 bg-[var(--accent)] hover:bg-white/10 text-left"
                >
                  <span className="font-semibold text-foreground">시도 {a.attempt}</span>
                  <div className="flex gap-1 flex-wrap">
                    {(a.passed || []).map((c) => (
                      <span key={c} className="px-1 rounded font-mono" style={{ background: "rgba(16,185,129,0.15)", color: "var(--grade-a)" }}>{c}</span>
                    ))}
                    {(a.warnings || []).map((w) => (
                      <span key={w.code} className="px-1 rounded font-mono" style={{ background: "rgba(245,158,11,0.15)", color: "var(--grade-b)" }}>{w.code}</span>
                    ))}
                    {(a.issues || []).map((iss) => (
                      <span key={iss.code} className="px-1 rounded font-mono" style={{ background: "rgba(239,68,68,0.15)", color: "var(--grade-c)" }}>{iss.code}</span>
                    ))}
                  </div>
                  <span className="ml-auto text-muted-foreground">{openIdx === i ? "▲" : "▼"}</span>
                </button>
                {openIdx === i && (
                  <div className="px-3 py-2 space-y-2">
                    {(a.warnings || []).map((w) => (
                      <div key={w.code} className="rounded px-2 py-1.5" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
                        <span className="font-semibold" style={{ color: "var(--grade-b)" }}>{w.code} {ITEM_LABELS[w.code] ? `— ${ITEM_LABELS[w.code]}` : ""}</span>
                        <span className="ml-1 text-muted-foreground">(경고)</span>
                        <div className="text-foreground mt-0.5">{w.reason}</div>
                      </div>
                    ))}
                    {(a.issues || []).map((iss) => (
                      <div key={iss.code} className="rounded px-2 py-1.5" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
                        <span className="font-semibold" style={{ color: "var(--grade-c)" }}>{iss.code} {ITEM_LABELS[iss.code] ? `— ${ITEM_LABELS[iss.code]}` : ""}</span>
                        <span className="ml-1 text-muted-foreground">(반려)</span>
                        <div className="text-foreground mt-0.5">{iss.reason}</div>
                      </div>
                    ))}
                    {a.retry_prompt && (
                      <div className="rounded px-2 py-1.5 bg-[var(--accent)]">
                        <div className="font-semibold text-muted-foreground mb-1">수정 지시문</div>
                        <div className="text-foreground whitespace-pre-wrap">{a.retry_prompt}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 최종 draft */}
      <div>
        <div className="font-semibold text-muted-foreground mb-1">최종 응답 (draft)</div>
        <div className="prose-response text-foreground border border-[var(--border)] rounded-lg p-3 glass">
          <ReactMarkdown>{entry.final_draft || entry.draft || "(없음)"}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
