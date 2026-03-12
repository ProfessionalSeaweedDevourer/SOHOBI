import { useState } from "react";
import ReactMarkdown from "react-markdown";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무" };
const DOMAIN_COLOR = {
  finance: "bg-emerald-100 text-emerald-700",
  admin: "bg-sky-100 text-sky-700",
  legal: "bg-amber-100 text-amber-700",
};
const ITEM_LABELS = {
  C1: "질문 응답성", C2: "완결성", C3: "내부 일관성", C4: "톤 적절성", C5: "할루시네이션 부재",
  F1: "수치 제시", F2: "단위 표기", F3: "가정 전제", F4: "불확실성", F5: "리스크 경고",
  G1: "근거 출처", G2: "법령 인용", G3: "조문 번호", G4: "면책 고지",
  A1: "지역 정보", A2: "업종 정보", A3: "수치 근거", A4: "기간 명시", A5: "출처 안내",
};

function fmtTs(ts) {
  if (!ts) return "-";
  try {
    return new Date(ts + "Z").toLocaleString("ko-KR", {
      month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return ts;
  }
}

/**
 * @param {{ entries: Array, loading: boolean }} props
 */
export default function LogTable({ entries, loading }) {
  const [selected, setSelected] = useState(null);

  if (loading) {
    return <div className="text-center py-20 text-slate-400 text-sm">로그 불러오는 중…</div>;
  }
  if (!entries || entries.length === 0) {
    return <div className="text-center py-20 text-slate-400 text-sm">로그가 없습니다.</div>;
  }

  return (
    <div className="flex gap-4 h-full">
      {/* 목록 */}
      <div className="w-full lg:w-1/2 overflow-y-auto flex flex-col gap-1.5 pr-1">
        {entries.map((entry, i) => {
          const isApproved = entry.status === "approved";
          const isSelected = selected === i;
          return (
            <button
              key={i}
              onClick={() => setSelected(isSelected ? null : i)}
              className={`
                w-full text-left text-xs border rounded-xl px-3 py-2.5 transition-colors
                ${isSelected
                  ? "border-violet-400 bg-violet-50"
                  : "border-slate-200 bg-white hover:bg-slate-50"}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${isApproved ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                  {isApproved ? "✅" : "❌"}
                </span>
                <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${DOMAIN_COLOR[entry.domain] || "bg-slate-100 text-slate-600"}`}>
                  {DOMAIN_KR[entry.domain] || entry.domain}
                </span>
                <span className="text-slate-400">{fmtTs(entry.ts)}</span>
                <span className="ml-auto text-slate-400">{(entry.latency_ms || 0).toFixed(0)}ms</span>
              </div>
              <div className="text-slate-700 truncate">{entry.question}</div>
              {(entry.retry_count > 0) && (
                <div className="text-slate-400 mt-0.5">재시도 {entry.retry_count}회</div>
              )}
            </button>
          );
        })}
      </div>

      {/* 상세 패널 */}
      <div className="hidden lg:flex lg:w-1/2 flex-col border border-slate-200 rounded-xl bg-white overflow-y-auto">
        {selected === null ? (
          <div className="flex-1 flex items-center justify-center text-slate-300 text-sm">
            항목을 선택하면 상세 내용이 표시됩니다.
          </div>
        ) : (
          <EntryDetail entry={entries[selected]} />
        )}
      </div>

      {/* 모바일: 선택 항목 상세 (모달 느낌) */}
      {selected !== null && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/30 flex items-end">
          <div className="bg-white w-full rounded-t-2xl max-h-[80vh] overflow-y-auto p-4">
            <button
              onClick={() => setSelected(null)}
              className="mb-3 text-sm text-slate-500"
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

  return (
    <div className="p-4 text-xs space-y-4">
      {/* 메타 */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className={`px-2 py-0.5 rounded-full font-semibold ${entry.status === "approved" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
          {entry.status}
        </span>
        <span className={`px-2 py-0.5 rounded-full ${DOMAIN_COLOR[entry.domain] || "bg-slate-100 text-slate-500"}`}>
          {DOMAIN_KR[entry.domain] || entry.domain}
        </span>
        <span className="text-slate-400">{fmtTs(entry.ts)}</span>
        <span className="text-slate-400">{(entry.latency_ms || 0).toFixed(0)}ms</span>
        <span className="text-slate-400">재시도 {entry.retry_count}회</span>
      </div>

      {/* 질문 */}
      <div>
        <div className="font-semibold text-slate-500 mb-1">질문</div>
        <div className="text-slate-800 leading-relaxed">{entry.question}</div>
      </div>

      {/* 거부 이력 */}
      {rejHist.length > 0 && (
        <div>
          <div className="font-semibold text-slate-500 mb-2">거부 이력</div>
          <div className="space-y-2">
            {rejHist.map((a, i) => (
              <div key={i} className="border border-slate-100 rounded-lg overflow-hidden">
                <button
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="w-full flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 text-left"
                >
                  <span className="font-semibold text-slate-600">시도 {a.attempt}</span>
                  <div className="flex gap-1 flex-wrap">
                    {(a.passed || []).map((c) => (
                      <span key={c} className="bg-green-100 text-green-700 px-1 rounded font-mono">{c}</span>
                    ))}
                    {(a.issues || []).map((iss) => (
                      <span key={iss.code} className="bg-red-100 text-red-600 px-1 rounded font-mono">{iss.code}</span>
                    ))}
                  </div>
                  <span className="ml-auto">{openIdx === i ? "▲" : "▼"}</span>
                </button>
                {openIdx === i && (
                  <div className="px-3 py-2 space-y-2">
                    {(a.issues || []).map((iss) => (
                      <div key={iss.code} className="bg-red-50 rounded px-2 py-1.5">
                        <span className="font-semibold text-red-700">{iss.code} {ITEM_LABELS[iss.code] ? `— ${ITEM_LABELS[iss.code]}` : ""}</span>
                        <div className="text-slate-600 mt-0.5">{iss.reason}</div>
                      </div>
                    ))}
                    {a.retry_prompt && (
                      <div className="bg-slate-50 rounded px-2 py-1.5">
                        <div className="font-semibold text-slate-500 mb-1">수정 지시문</div>
                        <div className="text-slate-600 whitespace-pre-wrap">{a.retry_prompt}</div>
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
        <div className="font-semibold text-slate-500 mb-1">최종 응답 (draft)</div>
        <div className="prose-response text-slate-700 border border-slate-100 rounded-lg p-3">
          <ReactMarkdown>{entry.final_draft || entry.draft || "(없음)"}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
