import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";

/**
 * @param {{ onSubmit: (q: string) => void, loading: boolean, placeholder?: string }} props
 * @param ref — 부모에서 ref.current.clear() 를 호출해 성공 시 입력창을 비울 수 있음
 */
const ChatInput = forwardRef(function ChatInput({ onSubmit, loading, placeholder }, ref) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // 부모가 호출할 수 있는 clear() 메서드 노출
  useImperativeHandle(ref, () => ({
    clear() { setValue(""); },
  }));

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
    // 입력창은 부모가 성공 후 clear()를 호출할 때 비워짐 (오류 시 보존)
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
});

export default ChatInput;
