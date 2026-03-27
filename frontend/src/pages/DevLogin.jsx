import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
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
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-slate-50">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-3xl mb-2">🛠</div>
          <h1 className="text-xl font-bold text-slate-800">개발자 모드</h1>
          <p className="text-sm text-slate-500 mt-1">
            내부 개발자 전용 영역입니다.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm"
        >
          <label className="block text-sm font-medium text-slate-700 mb-2">
            비밀번호
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="개발자 비밀번호를 입력하세요"
            autoFocus
            className="
              w-full border border-slate-200 rounded-lg px-4 py-2.5
              text-sm text-slate-800 placeholder-slate-400
              focus:outline-none focus:ring-2 focus:ring-violet-400
              disabled:opacity-50
            "
            disabled={loading}
          />

          {error && (
            <p className="mt-2 text-sm text-red-600">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="
              mt-4 w-full py-2.5 rounded-lg text-sm font-semibold
              bg-violet-600 text-white
              hover:bg-violet-700 active:scale-95 transition-all
              disabled:opacity-40 disabled:cursor-not-allowed
            "
          >
            {loading ? "확인 중…" : "입장"}
          </button>
        </form>

        <button
          onClick={() => navigate("/")}
          className="mt-4 w-full text-center text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          ← 홈으로 돌아가기
        </button>
      </div>
    </div>
  );
}
