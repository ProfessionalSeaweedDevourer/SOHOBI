import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { sendQuery } from "../api";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import SignoffPanel from "../components/SignoffPanel";

export default function DevChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(question) {
    setError(null);
    setLoading(true);
    try {
      const result = await sendQuery(question, 3, sessionId);
      if (result.session_id) setSessionId(result.session_id);
      setMessages((prev) => [
        ...prev,
        {
          question,
          domain: result.domain,
          status: result.status,
          grade: result.grade,
          confidenceNote: result.confidence_note,
          draft: result.draft,
          retryCount: result.retry_count,
          agentMs: result.agent_ms,
          signoffMs: result.signoff_ms,
          rejectionHistory: result.rejection_history || [],
        },
      ]);
      inputRef.current?.clear();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-slate-400 hover:text-slate-700 text-sm"
        >
          ← 홈
        </button>
        <span className="font-semibold text-slate-800">SOHOBI 개발자</span>
        <span className="ml-auto text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">
          개발자
        </span>
        <button
          onClick={() => navigate("/dev/logs")}
          className="text-xs text-slate-500 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-100 transition-colors"
        >
          📋 로그 뷰어
        </button>
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && !loading && (
          <div className="text-center mt-20 text-slate-400">
            <div className="text-4xl mb-3">🛠</div>
            <p className="text-sm">질문 입력 시 Sign-off 판정 결과가 함께 표시됩니다.</p>
            <p className="text-xs mt-1 text-slate-300">A/B/C 등급, 루브릭 항목별 통과·경고·반려 여부, 재시도 이력, 수정 지시문을 확인할 수 있습니다.</p>
          </div>
        )}

        <div className="flex flex-col gap-8">
          {messages.map((msg, i) => (
            <div key={i}>
              <ResponseCard
                question={msg.question}
                domain={msg.domain}
                status={msg.status}
                grade={msg.grade}
                confidenceNote={msg.confidenceNote}
                draft={msg.draft}
                retryCount={msg.retryCount}
                showMeta={true}
              />
              <SignoffPanel
                status={msg.status}
                grade={msg.grade}
                confidenceNote={msg.confidenceNote}
                retryCount={msg.retryCount}
                domain={msg.domain}
                agentMs={msg.agentMs}
                signoffMs={msg.signoffMs}
                rejectionHistory={msg.rejectionHistory}
              />
            </div>
          ))}

          {loading && (
            <div className="self-start flex items-center gap-2 text-slate-400 text-sm px-2">
              <span className="animate-spin text-base">⏳</span>
              에이전트 실행 중… (수 초에서 수십 초 소요)
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
              오류: {error}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-slate-50 border-t border-slate-100 px-4 py-3 max-w-3xl mx-auto w-full">
        <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} />
      </footer>
    </div>
  );
}
