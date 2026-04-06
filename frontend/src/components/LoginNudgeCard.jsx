export default function LoginNudgeCard({ onLogin, onDismiss }) {
  return (
    <div
      className="rounded-2xl px-5 py-4 border text-sm"
      style={{ background: "rgba(8,145,178,0.07)", borderColor: "rgba(8,145,178,0.2)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="font-semibold text-foreground mb-1">
            💾 이 상담, 기록으로 남기고 싶으신가요?
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed mb-3">
            로그인하면 오늘 상담 내용이 자동 저장됩니다.
          </p>
          <ul className="flex flex-col gap-1 mb-4">
            {[
              ["내 로그", "지난 상담 내역 언제든 재열람"],
              ["내 리포트", "질문 유형·통계 분석"],
              ["체크리스트", "창업 진행 현황 자동 동기화"],
            ].map(([label, desc]) => (
              <li key={label} className="flex items-center gap-2 text-xs text-muted-foreground">
                <span style={{ color: "var(--brand-blue)" }}>✓</span>
                <span>
                  <span className="font-medium text-foreground">{label}</span>
                  {" — "}
                  {desc}
                </span>
              </li>
            ))}
          </ul>
          <button
            onClick={onLogin}
            className="text-xs font-semibold px-4 py-2 rounded-xl transition-opacity hover:opacity-80"
            style={{ background: "var(--brand-blue)", color: "#fff" }}
          >
            Google로 로그인
          </button>
        </div>
        <button
          onClick={onDismiss}
          className="shrink-0 text-muted-foreground hover:text-foreground text-lg leading-none mt-0.5 transition-colors"
          aria-label="닫기"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
