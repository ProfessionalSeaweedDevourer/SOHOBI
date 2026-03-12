import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { sendQuery } from "../api";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";

export default function UserChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]); // [{question, domain, status, draft, retryCount}]
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
      const result = await sendQuery(question);
      setMessages((prev) => [
        ...prev,
        {
          question,
          domain: result.domain,
          status: result.status,
          draft: result.draft,
          retryCount: result.retry_count,
        },
      ]);
      inputRef.current?.clear(); // 성공 시에만 입력창 초기화
    } catch (e) {
      setError(e.message);
      // 오류 시 입력창 유지 — 사용자가 질문을 수정해 재시도 가능
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
              draft={msg.draft}
              retryCount={msg.retryCount}
              showMeta={false}
            />
          ))}

          {loading && (
            <div className="self-start flex items-center gap-2 text-slate-400 text-sm px-2">
              <span className="animate-spin text-base">⏳</span>
              분석 중…
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
