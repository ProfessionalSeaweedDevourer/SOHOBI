import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AuthCallback() {
  const { handleLoginSuccess } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Google OAuth redirect는 token을 URL fragment(#token=...)로 전달
    const hash = window.location.hash;
    const params = new URLSearchParams(hash.slice(1));
    const token = params.get("token");

    if (!token) {
      navigate("/user", { replace: true });
      return;
    }

    handleLoginSuccess(token).then(() => {
      navigate("/user", { replace: true });
    });
  }, [handleLoginSuccess, navigate]);

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      <div className="text-sm" style={{ color: "var(--muted-foreground)" }}>
        로그인 처리 중...
      </div>
    </div>
  );
}
