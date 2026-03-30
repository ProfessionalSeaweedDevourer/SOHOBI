import { useNavigate } from "react-router-dom";
import { isDevAuthenticated } from "../utils/devAuth";

const modes = [
  {
    path: "/user",
    label: "사용자 모드",
    icon: "💬",
    desc: "창업 관련 질문을 입력하면 AI 에이전트가 분석하고 답변합니다.",
    color: "hover:border-blue-400 hover:bg-blue-50",
    badge: "일반",
    badgeColor: "bg-blue-100 text-blue-700",
  },
  {
    path: "/map",
    label: "지도 모드",
    icon: "🗺️",
    desc: "서울 행정동 지도에서 상권을 탐색하고 AI 채팅으로 분석합니다.",
    color: "hover:border-emerald-400 hover:bg-emerald-50",
    badge: "지도",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    path: "/dev",
    label: "개발자 모드",
    icon: "🛠",
    desc: "에이전트 응답과 함께 Sign-off 판정 내역, 루브릭 통과 여부, 로그를 확인합니다.",
    color: "hover:border-violet-400 hover:bg-violet-50",
    badge: "개발자",
    badgeColor: "bg-violet-100 text-violet-700",
  },
];

export default function Home() {
  const navigate = useNavigate();

  function handleModeClick(path) {
    if (path === "/dev" && !isDevAuthenticated()) {
      navigate("/dev/login", { state: { from: { pathname: "/dev" } } });
      return;
    }
    navigate(path);
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-slate-50">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">SOHOBI</h1>
        <p className="text-slate-500 text-sm">
          소호비 — 1인 창업가를 위한 AI 상담 에이전트
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-6 w-full max-w-2xl">
        {modes.map((m) => (
          <button
            key={m.path}
            onClick={() => handleModeClick(m.path)}
            className={`
              flex-1 text-left border-2 border-slate-200 rounded-2xl p-8
              bg-white shadow-sm transition-all duration-150 cursor-pointer
              ${m.color}
            `}
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">{m.icon}</span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${m.badgeColor}`}
              >
                {m.badge}
              </span>
            </div>
            <div className="text-lg font-semibold text-slate-800 mb-1">
              {m.label}
            </div>
            <p className="text-sm text-slate-500 leading-relaxed">{m.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
