import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { CHECKLIST_ITEMS } from "../../constants/checklistItems";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _HEADERS = {
  "Content-Type": "application/json",
  ...(import.meta.env.VITE_API_KEY ? { "X-API-Key": import.meta.env.VITE_API_KEY } : {}),
};

function defaultItems() {
  return Object.fromEntries(
    CHECKLIST_ITEMS.map((item) => [item.id, { checked: false, source: null, checked_at: null }])
  );
}

/**
 * 창업 준비 체크리스트 상태 훅
 *
 * @param {string|null} sessionId
 * @returns {{ items, progress, toggleItem, syncFromDraft, loading }}
 */
export function useChecklistState(sessionId, enabled = true) {
  const [items, setItems] = useState(defaultItems);
  const [loading, setLoading] = useState(false);

  // 세션이 백엔드에 저장된 후에만 체크리스트 로드 (enabled 가드)
  useEffect(() => {
    if (!sessionId || !enabled) return;

    setLoading(true);
    fetch(`${BASE_URL}/api/checklist/${sessionId}`, { headers: _HEADERS })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.items) {
          setItems((prev) => ({ ...prev, ...data.items }));
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId, enabled]);

  // 수동 토글 — 낙관적 업데이트, 실패 시 롤백
  const toggleItem = useCallback(
    async (itemId) => {
      const current = items[itemId]?.checked ?? false;
      const next = !current;

      setItems((prev) => ({
        ...prev,
        [itemId]: { ...prev[itemId], checked: next, source: "manual" },
      }));

      if (!sessionId) return;

      try {
        const res = await fetch(`${BASE_URL}/api/checklist/${sessionId}`, {
          method: "PATCH",
          headers: _HEADERS,
          body: JSON.stringify({ item_id: itemId, checked: next, source: "manual" }),
        });
        if (!res.ok) throw new Error("patch failed");
      } catch {
        // 실패 시 롤백
        setItems((prev) => ({
          ...prev,
          [itemId]: { ...prev[itemId], checked: current },
        }));
      }
    },
    [items, sessionId]
  );

  // complete 이벤트의 checked_items 배열을 로컬 상태에 즉시 반영 + toast 알림
  const syncFromDraft = useCallback((checkedIds) => {
    if (!checkedIds?.length) return;
    setItems((prev) => {
      const next = { ...prev };
      const newlyChecked = [];
      for (const id of checkedIds) {
        if (next[id] && !next[id].checked) {
          next[id] = { ...next[id], checked: true, source: "auto" };
          newlyChecked.push(id);
        }
      }
      // 새로 체크된 항목이 있으면 toast 알림
      if (newlyChecked.length > 0) {
        const labels = newlyChecked
          .map((id) => CHECKLIST_ITEMS.find((i) => i.id === id)?.label)
          .filter(Boolean);
        toast("대화에서 다뤘어요!", {
          description: `✓ ${labels.join(", ")}`,
          duration: 4000,
        });
      }
      return next;
    });
  }, []);

  const progress = Object.values(items).filter((v) => v.checked).length;

  return { items, progress, toggleItem, syncFromDraft, loading };
}
