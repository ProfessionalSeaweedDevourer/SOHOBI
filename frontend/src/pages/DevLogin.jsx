import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { AnimatedBackground } from "../components/AnimatedBackground";
import {
  checkDevPassword,
  setDevAuthenticated,
  isDevAuthenticated,
} from "../utils/devAuth";

export default function DevLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const destination = location.state?.from?.pathname ?? "/dev";

  useEffect(() => {
    if (isDevAuthenticated()) {
      navigate(destination, { replace: true });
    }
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!password || loading) return;

    setLoading(true);
    setError(null);

    try {
      const ok = await checkDevPassword(password);
      if (ok) {
        setDevAuthenticated();
        navigate(destination, { replace: true });
      } else {
        setError("비밀번호가 올바르지 않습니다.");
      }
    } catch {
      setError("인증 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-background">
      <AnimatedBackground />
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-sm"
      >
        <div className="text-center mb-8">
          <div className="text-3xl mb-2">🛠</div>
          <h1 className="text-xl font-bold text-foreground">개발자 모드</h1>
          <p className="text-sm text-muted-foreground mt-1">
            내부 개발자 전용 영역입니다.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="glass-card rounded-2xl p-8"
        >
          <label className="block text-sm font-medium text-foreground mb-2">
            비밀번호
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="개발자 비밀번호를 입력하세요"
            autoFocus
            className="w-full border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground bg-[var(--input-background)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-teal)] disabled:opacity-50"
            disabled={loading}
          />

          {error && (
            <p className="mt-2 text-sm text-destructive">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="mt-4 w-full py-2.5 rounded-lg text-sm font-semibold text-white active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
          >
            {loading ? "확인 중…" : "입장"}
          </button>
        </form>

        <button
          onClick={() => navigate("/")}
          className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 홈으로 돌아가기
        </button>
      </motion.div>
    </div>
  );
}
