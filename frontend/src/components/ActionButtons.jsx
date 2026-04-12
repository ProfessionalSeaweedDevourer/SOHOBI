/**
 * ActionButtons.jsx
 * suggested_actions 버튼 목록 렌더링.
 * 버튼 클릭 시 onAction(value) 호출.
 */
export default function ActionButtons({ actions, onAction, disabled }) {
  if (!actions?.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {actions.map((action, idx) => (
        <button
          key={idx}
          onClick={() => onAction(action.value)}
          disabled={disabled}
          className="text-xs px-3 py-1.5 rounded-full border transition-all
                     hover:opacity-80 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: "rgba(20,184,166,0.1)",
            borderColor: "rgba(20,184,166,0.4)",
            color: "var(--brand-teal, #14b8a6)",
          }}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
