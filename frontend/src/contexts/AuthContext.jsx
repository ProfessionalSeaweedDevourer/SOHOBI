import { createContext, useContext, useState, useEffect, useCallback } from "react";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const JWT_KEY = "sohobi_jwt";
const SESSION_KEY = "sohobi_session_id";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // JWT 토큰 → /auth/me 로 유저 정보 복원
  useEffect(() => {
    const token = localStorage.getItem(JWT_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    fetch(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setUser({ ...data, token });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // 로그인 완료 후 호출 (AuthCallback에서 사용)
  const handleLoginSuccess = useCallback(async (token) => {
    localStorage.setItem(JWT_KEY, token);
    const r = await fetch(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) return;
    const data = await r.json();
    setUser({ ...data, token });

    // 기존 익명 세션이 있으면 귀속
    const sessionId = localStorage.getItem(SESSION_KEY);
    if (sessionId) {
      fetch(`${BASE_URL}/auth/link-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
  }, []);

  const login = useCallback(() => {
    window.location.href = `${BASE_URL}/auth/google`;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(JWT_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, handleLoginSuccess }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
