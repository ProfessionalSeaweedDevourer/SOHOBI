import { useEffect } from "react";
import { useDismissible } from "../hooks/useDismissible";
import { trackEvent } from "../utils/trackEvent";

const VERSION = "2026_04_20";
const STORAGE_KEY = `sohobi_maintenance_${VERSION}`;

export default function MaintenanceNotice() {
  const [visible, dismiss] = useDismissible(STORAGE_KEY, { storage: "local" });

  useEffect(() => {
    if (!visible) return;
    trackEvent("maintenance_notice_view", { version: VERSION });
  }, [visible]);

  if (!visible) return null;

  const handleDismiss = () => {
    trackEvent("maintenance_notice_dismiss", { version: VERSION });
    dismiss();
  };

  return (
    <aside
      role="status"
      aria-label="서비스 점검 안내"
      className="mb-6 rounded-2xl px-5 py-4 border text-sm"
      style={{ background: "rgba(249,115,22,0.07)", borderColor: "rgba(249,115,22,0.25)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-foreground mb-1">🔧 일부 서비스 점검 안내</div>
          <p className="text-muted-foreground leading-relaxed">
            법무·세무 및 정부지원 검색 서비스가 일시 점검 중입니다. 복구 예정은 약 1주 이내이며,
            재무 시뮬레이션·상권 분석·행정 절차 안내 등 다른 상담은 정상 이용하실 수 있습니다.
          </p>
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          className="shrink-0 text-muted-foreground hover:text-foreground text-lg leading-none mt-0.5 transition-colors"
          aria-label="닫기"
        >
          ✕
        </button>
      </div>
    </aside>
  );
}
