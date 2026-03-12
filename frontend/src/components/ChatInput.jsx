import { useState, useRef, useEffect } from "react";

/**
 * @param {{ onSubmit: (q: string) => void, loading: boolean, placeholder?: string }} props
 */
export default function ChatInput({ onSubmit, loading, placeholder }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // 높이 자동 조절
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <div className="flex items-end gap-2 border border-slate-200 rounded-xl bg-white px-4 py-3 shadow-sm">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={loading}
        placeholder={placeholder || "질문을 입력하세요… (Shift+Enter: 줄바꿈)"}
        className="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none leading-relaxed disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={loading || !value.trim()}
        className="
          shrink-0 px-4 py-2 rounded-lg text-sm font-semibold
          bg-slate-800 text-white
          disabled:opacity-40 disabled:cursor-not-allowed
          hover:bg-slate-700 active:scale-95 transition-all
        "
      >
        {loading ? "처리 중…" : "전송"}
      </button>
    </div>
  );
}
