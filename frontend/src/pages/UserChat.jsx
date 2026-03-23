import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { streamQuery } from "../api";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import ProgressPanel from "../components/ProgressPanel";

export default function UserChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(question) {
    setError(null);
    setLoading(true);
    setActiveEvents([]);

    let finalResult = null;

    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        setActiveEvents(prev => [...prev, { event: eventName, ...data }]);
        if (eventName === "domain_classified" && data.session_id) {
          setSessionId(data.session_id);
        }
        if (eventName === "complete") {
          finalResult = data;
        }
      });
    } catch (e) {
      setError(e.message);
      setLoading(false);
      return;
    }

    if (finalResult) {
      setMessages(prev => [
        ...prev,
        {
          question,
          domain:         finalResult.domain,
          status:         finalResult.status,
          grade:          finalResult.grade,
          confidenceNote: finalResult.confidence_note,
          draft:          finalResult.draft,
          retryCount:     finalResult.retry_count,
        },
      ]);
    }

    setActiveEvents([]);
    setLoading(false);
    inputRef.current?.clear();
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
        <span className="font-semibold text-slate-800">SOHOBI 상담</span>
        <span className="ml-auto text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">사용자</span>
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && !loading && (
          <div className="text-center mt-20 text-slate-400">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-sm">창업 관련 질문을 입력해 보세요.</p>
            <div className="mt-4 flex flex-col gap-2 items-center">
              {[
                "월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집 창업 시 수익성은?",
                "홍대 카페 상권 분석해 줘",
                "임대차 계약 시 권리금 보호 규정이 있나요?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleSubmit(q)}
                  className="text-xs text-slate-500 border border-slate-200 rounded-full px-4 py-1.5 hover:bg-slate-100 transition-colors max-w-xs text-left"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {messages.map((msg, i) => (
            <ResponseCard
              key={i}
              question={msg.question}
              domain={msg.domain}
              status={msg.status}
              grade={msg.grade}
              confidenceNote={msg.confidenceNote}
              draft={msg.draft}
              retryCount={msg.retryCount}
              showMeta={false}
            />
          ))}

          {loading && (
            <div className="self-start bg-white border border-slate-100 rounded-xl px-4 py-3 text-sm w-full max-w-md">
              <ProgressPanel events={activeEvents} detailed={false} />
              {activeEvents.length === 0 && (
                <div className="flex items-center gap-2 text-slate-400 text-xs">
                  <span className="inline-block w-3 h-3 border-2 border-slate-200 border-t-blue-400 rounded-full animate-spin" />
                  분석 준비 중…
                </div>
              )}
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
