import { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ArrowRight, Gift } from "lucide-react";
import { useDismissible } from "../hooks/useDismissible";
import { trackEvent } from "../utils/trackEvent";

const SURVEY_URL =
  "https://forms.office.com/pages/responsepage.aspx?id=OkauYhKf306FRE9so4NFJBKV4WxfV5tMpfVaLEYVJOJUMUowVTY3SDY0QTBaRUdEMVYwNUIySlY3OC4u&route=shorturl";
const CURRENT = 79;
const TARGET = 100;

export default function SurveyBanner({ bottomOffset = "bottom-6" }) {
  const [visible, dismiss] = useDismissible("sohobi_survey_closed", { storage: "session" });

  const filled = Math.min((CURRENT / TARGET) * 100, 100);
  const done = CURRENT >= TARGET;

  useEffect(() => {
    if (!visible) return;
    trackEvent("survey_banner_view", { current: CURRENT, target: TARGET });
  }, [visible]);

  const handleClick = () => {
    trackEvent("survey_banner_click", { current: CURRENT, target: TARGET });
    window.open(SURVEY_URL, "_blank", "noopener,noreferrer");
  };

  const handleDismiss = () => {
    trackEvent("survey_banner_dismiss", { current: CURRENT, target: TARGET });
    dismiss();
  };

  const accent = done ? "var(--brand-teal)" : "var(--brand-orange)";

  return (
    <AnimatePresence>
      {visible && (
        <motion.aside
          role="complementary"
          aria-label="SOHOBI 사용자 설문"
          initial={{ opacity: 0, y: 20, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.97 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className={`glass shadow-elevated fixed right-6 ${bottomOffset} z-40 w-[340px] max-w-[calc(100vw-3rem)] rounded-2xl border border-white/20 p-5`}
        >
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="닫기"
            className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-muted-foreground transition-colors hover:bg-white/20 hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>

          <div
            className="mb-2.5 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
            style={{
              color: accent,
              borderColor: `color-mix(in srgb, ${accent} 25%, transparent)`,
              background: `color-mix(in srgb, ${accent} 15%, transparent)`,
            }}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${done ? "" : "animate-pulse"}`}
              style={{ background: accent }}
            />
            {done ? "목표 달성" : "모집 중"}
          </div>

          <p className="mb-1 text-[15px] font-bold leading-snug text-foreground">
            {done ? "여러분 덕분에 목표를 달성했어요" : "SOHOBI를 더 좋게 만들고 싶어요"}
          </p>
          <p className="mb-3.5 text-xs leading-relaxed text-muted-foreground">
            {done
              ? `총 ${CURRENT}명의 소상공인 분들이 의견을 주셨습니다. 소중한 피드백으로 계속 개선하겠습니다.`
              : "5분이면 충분합니다. 실제 사용 경험을 나눠 주시면 서비스 개선에 직접 반영됩니다."}
          </p>

          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">응답 현황</span>
            <span className="text-xs font-semibold" style={{ color: accent }}>
              {CURRENT} / {TARGET}명
            </span>
          </div>
          <div className="mb-3.5 h-1 w-full overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${filled}%` }}
              transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
              style={{
                background: done
                  ? "linear-gradient(90deg, var(--brand-teal), color-mix(in srgb, var(--brand-teal) 60%, white))"
                  : "linear-gradient(90deg, var(--brand-orange), color-mix(in srgb, var(--brand-orange) 60%, white))",
              }}
            />
          </div>

          <button
            type="button"
            onClick={handleClick}
            className="group flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white shadow-md transition-all hover:brightness-110 hover:-translate-y-px"
            style={{
              background: done
                ? "linear-gradient(135deg, var(--brand-teal), color-mix(in srgb, var(--brand-teal) 70%, black))"
                : "linear-gradient(135deg, var(--brand-orange), color-mix(in srgb, var(--brand-orange) 70%, black))",
            }}
          >
            {done ? "추가 의견 남기기" : "설문 참여하기"}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>

          <div className="mt-2.5 flex items-center justify-center gap-1.5 text-[10.5px] text-muted-foreground/80">
            <Gift className="h-3 w-3" />
            <span>참여자 추첨 — 스타벅스 1만원 상품권 지급</span>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
