import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";

const ChatInput = forwardRef(function ChatInput({ onSubmit, loading, placeholder }, ref) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  useImperativeHandle(ref, () => ({
    clear() { setValue(""); },
  }));

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
  }

  return (
    <div className="flex items-end gap-2 glass-card rounded-xl px-4 py-3">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={loading}
        placeholder={placeholder || "질문을 입력하세요… (Shift+Enter: 줄바꿈)"}
        className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none leading-relaxed disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={loading || !value.trim()}
        className="shrink-0 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-40 disabled:cursor-not-allowed active:scale-95 transition-all"
        style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
      >
        {loading ? "처리 중…" : "전송"}
      </button>
    </div>
  );
});

export default ChatInput;
