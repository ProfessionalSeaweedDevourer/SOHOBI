import { useState, useCallback } from "react";

export function useDismissible(key, { storage = "local" } = {}) {
  const store = storage === "session" ? sessionStorage : localStorage;
  const [visible, setVisible] = useState(() => !store.getItem(key));

  const dismiss = useCallback(() => {
    store.setItem(key, "1");
    setVisible(false);
  }, [key, store]);

  return [visible, dismiss];
}
