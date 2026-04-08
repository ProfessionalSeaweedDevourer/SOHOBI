/**
 * shimmer 배경 + floating orb 2개를 가진 glass CTA 래퍼
 * Landing/Features/서브페이지 CTA 섹션에서 공통으로 사용
 *
 * @param {string} [orbSize="w-40 h-40"]  - orb 크기 Tailwind 클래스
 * @param {string} [className]            - 추가 클래스 (padding 등)
 * @param {React.ReactNode} children
 */
export function GlowCTA({ orbSize = "w-40 h-40", className = "", children }) {
  return (
    <div className={`glass rounded-3xl relative overflow-hidden ${className}`}>
      {/* shimmer 배경 */}
      <div
        className="absolute inset-0 bg-gradient-to-r from-[var(--brand-blue)] via-[var(--brand-teal)] to-[var(--brand-blue)] opacity-10 animate-shimmer"
        style={{ backgroundSize: "200% 100%" }}
      />
      {/* floating orbs — will-change로 GPU 레이어 승격 */}
      <div
        className={`absolute top-0 left-1/4 ${orbSize} bg-[var(--brand-blue)] rounded-full blur-3xl opacity-20 animate-float`}
        style={{ willChange: "transform", transform: "translateZ(0)" }}
      />
      <div
        className={`absolute bottom-0 right-1/4 ${orbSize} bg-[var(--brand-teal)] rounded-full blur-3xl opacity-20 animate-float`}
        style={{ willChange: "transform", transform: "translateZ(0)", animationDelay: "1s" }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
