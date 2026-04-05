import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { streamQuery } from "../api";
import { interpretError } from "../utils/errorInterpreter";
import { trackEvent } from "../utils/trackEvent";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import ProgressPanel from "../components/ProgressPanel";
import { ThemeToggle } from "../components/ThemeToggle";
import StartupChecklist from "../components/checklist/StartupChecklist";
import ChecklistProgress from "../components/checklist/ChecklistProgress";
import { useChecklistState } from "../components/checklist/useChecklistState";

const DOMAIN_CARDS = [
  {
    id: "admin",
    icon: "📋",
    label: "행정 절차",
    desc: "영업신고·위생교육·사업자등록",
    color: "var(--brand-blue)",
    colorBg: "rgba(8,145,178,0.08)",
    borderColor: "rgba(8,145,178,0.25)",
    questions: [
      "카페 창업 시 영업신고 절차와 필요 서류를 처음부터 알려줘",
      "일반음식점과 휴게음식점의 차이와 신고 방법은?",
    ],
  },
  {
    id: "finance",
    icon: "📊",
    label: "재무 시뮬레이션",
    desc: "수익성·손익분기·투자회수 분석",
    color: "var(--brand-orange)",
    colorBg: "rgba(249,115,22,0.08)",
    borderColor: "rgba(249,115,22,0.25)",
    questions: [
      "월매출 700만원, 재료비 200만원, 직원 1명으로 분식집 창업 시 수익성은?",
      "보증금 5천만원 월세 180만원 카페, 손익분기점 계산해 줘",
    ],
  },
  {
    id: "legal",
    icon: "⚖️",
    label: "법무 정보",
    desc: "임대차·권리금·상가임대차보호법",
    color: "#8b5cf6",
    colorBg: "rgba(139,92,246,0.08)",
    borderColor: "rgba(139,92,246,0.25)",
    questions: [
      "임대차 계약 시 권리금 보호 규정이 있나요?",
      "임대차 3년 후 건물주가 갱신을 거절할 수 있는 경우는?",
    ],
  },
  {
    id: "location",
    icon: "📍",
    label: "상권 분석",
    desc: "서울 2025 Q4 데이터 기반 분석",
    color: "var(--brand-teal)",
    colorBg: "rgba(20,184,166,0.08)",
    borderColor: "rgba(20,184,166,0.25)",
    questions: [
      "홍대 카페 상권 분석해 줘",
      "마포구 치킨집 월평균 매출과 경쟁 현황 알려줘",
    ],
  },
  {
    id: "gov",
    icon: "🎁",
    label: "정부 지원",
    desc: "보조금·창업패키지·대출·신용보증",
    color: "#ec4899",
    colorBg: "rgba(236,72,153,0.08)",
    borderColor: "rgba(236,72,153,0.25)",
    questions: [
      "청년 창업자가 신청할 수 있는 정부 지원금 종류 알려줘",
      "소상공인 정책자금 대출 조건과 금리가 어떻게 되나요?",
    ],
  },
];

const PLACEHOLDER_QUESTIONS = [
  // 행정 (20)
  "카페 창업 전 구청에 가기 전에 미리 확인해야 할 행정 절차가 뭔가요?",
  "사업자등록증 발급, 어디서 어떻게 신청하나요?",
  "일반음식점과 휴게음식점 차이가 뭔지, 어떻게 구분해서 신고해야 하나요?",
  "음식점 위생교육은 언제까지 이수해야 하나요?",
  "주류 판매하려면 영업신고 외에 추가 허가가 필요한가요?",
  "배달 전문점만 운영할 경우 영업신고 방식이 다른가요?",
  "개인사업자로 할지 법인으로 할지 세금 측면에서 뭐가 유리한가요?",
  "직원 한 명 고용 시 4대보험 가입 절차와 비용 부담이 어떻게 되나요?",
  "음식점 시설 기준, 조리장 면적이나 환기 시설 규정이 있나요?",
  "외국인 직원 채용하려는데 신고 절차가 어떻게 되나요?",
  "간판 설치할 때 허가가 필요한 경우와 신고만 해도 되는 경우 알려줘",
  "포장마차 형태로 노점 영업하려면 어떤 허가가 필요한가요?",
  "음식점 리모델링 후 재검사나 변경 신고가 필요한가요?",
  "영업신고 후 상호명 바꾸려면 어떤 절차를 거쳐야 하나요?",
  "아르바이트 고용 시 근로계약서 작성 의무가 있나요?",
  "식품위생법 위반 시 행정처분 단계가 어떻게 되나요?",
  "화재 안전 관련해서 음식점이 갖춰야 할 소방 시설 기준은?",
  "음식점 내 CCTV 설치 의무 규정이 있나요?",
  "HACCP 인증을 받으면 어떤 실질적 혜택이 있나요?",
  "창업 전 세무사 상담이 꼭 필요한가요, 혼자 처리 가능한 범위는?",

  // 재무 (25)
  "월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집 수익성은?",
  "보증금 5천만원 월세 180만원 카페, 손익분기점이 어떻게 되나요?",
  "초기 창업 비용 8천만원, 예상 월 순이익 200만원이면 투자 회수까지 몇 달?",
  "직원 2명 고용한 카페, 4대보험 포함 실제 인건비 월 총액이 얼마나 되나요?",
  "배달 위주 치킨집, 배달 플랫폼 수수료 15% 빼면 실제 마진이 얼마나 남나요?",
  "월 순이익 300만원을 목표로 할 때 필요한 최소 매출 계산해 줘 (재료비율 35%)",
  "창업 자금 5천만원 중 2천만원 대출 받으면 월 상환금 포함해서 수익성이 어떤가요?",
  "프랜차이즈 가맹비 3천만원 포함한 총 창업 비용 대비 수익성 분석해 줘",
  "권리금 5천만원 주고 인수한 가게, 손익분기점까지 몇 달이나 걸릴까?",
  "직원 없이 혼자 운영하는 월세 150만원 분식집, 최소 매출 목표는?",
  "아르바이트 2명 일 8시간씩 주 5일, 최저임금 기준 월 인건비 계산해 줘",
  "배달앱 입점 수수료와 포장재비 포함하면 배달 매출 실질 수익률이 얼마나 되나요?",
  "카드 수수료와 부가세 납부 감안하면 실제 손에 쥐는 금액이 달라지나요?",
  "좌석 10개 매장, 하루 회전율 4회 기준 월 예상 매출이 얼마나 되나요?",
  "매출이 계절마다 들쑥날쑥한 카페, 연간 현금흐름 시뮬레이션 해줘",
  "임대료를 월 30만원 낮추면 연간 수익에 어떤 차이가 생기나요?",
  "메뉴 가격 10% 올리면 손님이 좀 줄어도 수익이 나아질 수 있나요?",
  "주말 매출이 주중의 2.5배인 가게, 월 평균 매출 시뮬레이션 해줘",
  "첫 6개월 매출 0원에서 시작해서 매달 100만원씩 증가한다면 생존 가능한가요?",
  "외식업 3년 생존율 감안한 최악/보통/최선 시나리오별 수익 전망 분석해 줘",
  "점심 특선만 팔고 오후엔 문 닫는 운영 방식, 수익성이 나올 수 있을까요?",
  "직원 월급 250만원을 280만원으로 올리면 손익분기점이 얼마나 올라가나요?",
  "테이크아웃 전문 커피숍, 월 2천 잔 판매 목표일 때 수익 계산해 줘",
  "월세가 매출의 20%를 넘으면 위험한 건가요? 적정 임대료 비율이 궁금해요",
  "명절 연휴 영업 중단 기간 포함해서 분기별 현금흐름 예측해 줘",

  // 법무 (20)
  "임대차 계약 시 권리금 보호 규정이 어떻게 되나요?",
  "건물주가 3년 계약 만료 후 갱신을 거절할 수 있는 경우가 있나요?",
  "상가건물임대차보호법이 적용되는 조건과 보호 내용이 뭔가요?",
  "계약서에 '원상복구 의무' 조항이 있는데, 어디까지 책임져야 하나요?",
  "월세를 3개월 연체하면 바로 계약 해지되나요?",
  "임대료 인상 요구를 받았는데, 거절할 수 있는 법적 근거가 있나요?",
  "건물 주인이 바뀌면 기존 임대차 계약은 어떻게 되나요?",
  "확정일자를 받아두면 어떤 상황에서 보호를 받을 수 있나요?",
  "권리금 계약서 작성할 때 특히 주의해야 할 조항이 뭔가요?",
  "누수나 배관 문제가 생겼는데 수리 비용 책임이 임차인인지 건물주인지요?",
  "아르바이트생 4대보험 의무 가입, 몇 시간 이상 일해야 해당되나요?",
  "직원 해고할 때 예고 기간과 퇴직금 지급 기준이 어떻게 되나요?",
  "손님이 식중독에 걸렸다고 신고하면 업주가 어떤 법적 책임을 지나요?",
  "배달앱 리뷰에 명백한 허위 사실이 적혀 있을 때 법적으로 대응할 수 있나요?",
  "프랜차이즈 계약 전에 불공정 조항을 걸러내려면 뭘 확인해야 하나요?",
  "계약 기간 중 자진 폐업하면 위약금을 물어야 하나요?",
  "상호 등록 없이 사용하다 다른 가게와 이름이 겹쳤을 때 어떻게 되나요?",
  "명의를 지인에게 빌려서 사업자등록하면 법적으로 문제가 되나요?",
  "근로기준법상 음식점 직원의 휴게시간 및 연장근무 수당 규정은?",
  "임대차 기간 중 건물주가 재건축을 이유로 나가라고 하면 어떻게 대응하나요?",

  // 상권 (20)
  "홍대 카페 상권 분석해 줘, 유동인구랑 경쟁 현황 포함해서",
  "마포구에서 치킨집 창업하기 좋은 동네가 어딘지 상권 데이터로 알려줘",
  "강남역 vs 신촌, 분식집 창업 입지로 어디가 더 유리한가요?",
  "성수동 카페 상권 최근 개폐업률이 어떻게 되나요?",
  "종로3가 한식당 상권, 주요 고객층과 평균 매출 데이터 알려줘",
  "서울 망원동 골목 카페 상권, 주변 경쟁 업체 밀도는 어떤가요?",
  "신림동 대학가 근처 분식집 상권, 수요가 충분한지 궁금해요",
  "송파구에서 경쟁 업체가 적은 치킨집 입지를 찾을 수 있나요?",
  "영등포 타임스퀘어 인근 식당 상권, 평일 점심 vs 주말 저녁 유동인구 차이는?",
  "연남동 vs 연희동, 카페 창업하기에 어느 쪽 상권이 나을까요?",
  "노원구 중계동 학원가 앞 분식집, 방학 시즌 매출 변동이 얼마나 큰가요?",
  "관악구 봉천동 고시촌 식당 상권 특성과 평균 매출은?",
  "구로 디지털단지 직장인 대상 점심 식당 상권 분석해 줘",
  "동대문 의류 상권 인근 식당, 새벽 영업 수요가 있나요?",
  "은평구 응암동 배달 전문 치킨집 수요가 충분한가요?",
  "동작구 흑석동 대학가 근처 김밥·분식집 개폐업률 알려줘",
  "중구 을지로 카페 상권, 직장인 수요 기준으로 오전 vs 오후 매출 비중이 어떤가요?",
  "강서구 방화동 일대 한식당 상권 분석, 경쟁업체 현황 포함해서",
  "용산구 이태원 음식점 상권, 외국인 고객 비중과 최근 매출 흐름은?",
  "성북구 길음동 주택가 인근 배달 전문 분식집, 수요가 있는 상권인가요?",

  // 정부지원 (15)
  "청년 창업자가 신청할 수 있는 정부 지원금과 대출 종류를 알려줘",
  "소상공인 정책자금 대출 신청 조건과 현재 금리가 어떻게 되나요?",
  "중장년(40대 이상) 창업자도 받을 수 있는 정부 지원 사업이 있나요?",
  "한 번 폐업했다가 재창업하는 경우에도 지원받을 수 있나요?",
  "창업 초기 임대료를 지원해 주는 정부 프로그램이 있나요?",
  "소상공인시장진흥공단에서 제공하는 무료 교육이나 컨설팅이 뭐가 있나요?",
  "고용노동부 청년 고용 지원금을 음식점에서도 받을 수 있나요?",
  "지역 신용보증재단을 통한 대출 보증 절차가 어떻게 되나요?",
  "창업진흥원 창업패키지 신청 자격이 어떻게 되고 지원 규모는 얼마나 되나요?",
  "노란우산공제에 가입하면 구체적으로 어떤 혜택을 받을 수 있나요?",
  "전통시장 내에 창업하면 추가 지원 혜택이 있나요?",
  "여성 창업자를 위한 별도 정부 지원 사업이 있나요?",
  "식품업 창업자에게 특화된 지원 정책이 있나요?",
  "창업 실패 후 재기를 돕는 소상공인 재기 지원 프로그램이 뭔가요?",
  "무료 창업 멘토링이나 전문가 상담을 받을 수 있는 공공기관이 어디 있나요?",
];

export default function UserChat() {
  const navigate = useNavigate();
  const { user, login, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [latestParams, setLatestParams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [showBanner, setShowBanner] = useState(() => !localStorage.getItem("sohobi_tip_dismissed"));
  const [showSamples, setShowSamples] = useState(false);
  const [placeholder] = useState(
    () => PLACEHOLDER_QUESTIONS[Math.floor(Math.random() * PLACEHOLDER_QUESTIONS.length)]
  );
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const userMenuRef = useRef(null);
  const { items: checklistItems, progress: checklistProgress, toggleItem, syncFromDraft } = useChecklistState(sessionId);

  useEffect(() => {
    if (!userMenuOpen) return;
    function handleClickOutside(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userMenuOpen]);

  useEffect(() => {
    trackEvent('feature_discovery', { page: 'user_chat' });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function dismissBanner() {
    localStorage.setItem("sohobi_tip_dismissed", "1");
    setShowBanner(false);
  }

  async function handleSubmit(question) {
    trackEvent('agent_query', { session_id: sessionId, page: 'user_chat' });
    setPendingQuestion(question);
    setLoading(true);
    setActiveEvents([]);

    let finalResult = null;

    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        if (eventName === "error") {
          setPendingQuestion(null);
          setMessages(prev => [
            ...prev,
            { question, status: "error", draft: interpretError(data.message || data.error || "") },
          ]);
          return;
        }
        setActiveEvents(prev => [...prev, { event: eventName, ...data }]);
        if (eventName === "domain_classified" && data.session_id) {
          setSessionId(data.session_id);
          localStorage.setItem("sohobi_session_id", data.session_id);
        }
        if (eventName === "complete") {
          finalResult = data;
          if (data.checked_items?.length) {
            syncFromDraft(data.checked_items);
          }
        }
      }, latestParams);
    } catch (e) {
      setPendingQuestion(null);
      setMessages(prev => [
        ...prev,
        { question, status: "error", draft: interpretError(e.message) },
      ]);
      setActiveEvents([]);
      setLoading(false);
      inputRef.current?.clear();
      return;
    }

    setPendingQuestion(null);

    if (finalResult) {
      setMessages(prev => [
        ...prev,
        {
          question,
          domain:         finalResult.domain,
          status:         finalResult.status,
          grade:          finalResult.grade,
          confidenceNote: finalResult.confidence_note,
          draft:          finalResult.draft,
          retryCount:     finalResult.retry_count,
          chart:          finalResult.chart || null,
          charts:         finalResult.charts || [],
          requestId:      finalResult.request_id || null,
          sessionId:      finalResult.session_id || null,
        },
      ]);
      if (finalResult.updated_params) setLatestParams(finalResult.updated_params);
    }

    setActiveEvents([]);
    setLoading(false);
    inputRef.current?.clear();
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          ← 홈
        </button>
        <span className="font-semibold text-foreground">SOHOBI 상담</span>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: "rgba(8,145,178,0.15)", color: "var(--brand-blue)" }}
        >
          사용자
        </span>
        <a
          href="/my-report"
          className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-[var(--muted)]"
          style={{ borderColor: "var(--border)", color: "var(--muted-foreground)", textDecoration: "none" }}
        >
          내 리포트 📊
        </a>
        <a
          href="/roadmap"
          className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-[var(--muted)]"
          style={{ borderColor: "var(--border)", color: "var(--muted-foreground)", textDecoration: "none" }}
        >
          로드맵 🗳️
        </a>
        {user ? (
          <>
            <a
              href="/my-logs"
              className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-[var(--muted)]"
              style={{ borderColor: "var(--border)", color: "var(--muted-foreground)", textDecoration: "none" }}
            >
              내 로그 📋
            </a>
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen((v) => !v)}
                className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-[var(--muted)] max-w-[6rem] truncate"
                style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
                title={user.email}
              >
                {user.name || user.email} ▾
              </button>
              {userMenuOpen && (
                <div
                  className="absolute right-0 top-full mt-1 rounded-xl border shadow-lg z-50 overflow-hidden"
                  style={{ background: "var(--card)", borderColor: "var(--border)", minWidth: "7rem" }}
                >
                  <div className="px-3 py-2 text-xs border-b truncate" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
                    {user.email}
                  </div>
                  <button
                    onClick={() => { setUserMenuOpen(false); logout(); }}
                    className="w-full text-left px-3 py-2 text-xs transition-colors hover:bg-[var(--muted)]"
                    style={{ color: "var(--foreground)" }}
                  >
                    로그아웃
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <button
            onClick={login}
            className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-[var(--muted)]"
            style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
          >
            로그인
          </button>
        )}
        <ThemeToggle />
      </header>

      {/* 대화 영역 + 사이드패널 */}
      <div className="flex-1 flex overflow-hidden max-w-5xl mx-auto w-full">
      <main className="flex-1 overflow-y-auto px-4 py-6 min-w-0">
        {messages.length === 0 && !loading && !pendingQuestion && (
          <div className="mt-6">
            {/* 첫 방문 팁 배너 */}
            {showBanner && (
              <div
                className="mb-6 rounded-2xl px-5 py-4 border text-sm"
                style={{ background: "rgba(8,145,178,0.07)", borderColor: "rgba(8,145,178,0.2)" }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-foreground mb-1">💡 이렇게 질문하면 더 정확해요</div>
                    <p className="text-muted-foreground leading-relaxed">
                      업종·지역·수치를 함께 적어주실수록 정확한 분석을 드립니다.
                      재무 질문은 매출·비용·인건비를, 상권 질문은 동네 이름과 업종을 포함해 보세요.
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground italic">
                      예: "강남 카페, 보증금 5천만원 월세 200만원, 직원 1명일 때 수익성과 손익분기점 알려줘"
                    </p>
                    <button
                      onClick={() => navigate("/features")}
                      className="mt-3 text-xs font-medium underline underline-offset-2"
                      style={{ color: "var(--brand-blue)" }}
                    >
                      SOHOBI 기능 전체 안내 →
                    </button>
                  </div>
                  <button
                    onClick={dismissBanner}
                    className="shrink-0 text-muted-foreground hover:text-foreground text-lg leading-none mt-0.5 transition-colors"
                    aria-label="닫기"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            {/* 도메인 카드 그리드 */}
            <div className="text-center mb-5">
              <div className="text-3xl mb-2">💬</div>
              <p className="text-sm text-muted-foreground">무엇이 궁금하신가요? 아래 영역에서 예시 질문을 골라보세요.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DOMAIN_CARDS.map(card => (
                <div
                  key={card.id}
                  className="rounded-2xl p-4 border"
                  style={{ background: card.colorBg, borderColor: card.borderColor }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xl">{card.icon}</span>
                    <div>
                      <div className="font-semibold text-sm text-foreground">{card.label}</div>
                      <div className="text-xs text-muted-foreground">{card.desc}</div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {card.questions.map(q => (
                      <button
                        key={q}
                        onClick={() => handleSubmit(q)}
                        className="text-left text-xs px-3 py-2 rounded-xl transition-opacity hover:opacity-70 leading-relaxed"
                        style={{ background: "rgba(255,255,255,0.08)", color: "var(--foreground)" }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {messages.map((msg, i) => (
            <ResponseCard
              key={i}
              question={msg.question}
              domain={msg.domain}
              status={msg.status}
              grade={msg.grade}
              confidenceNote={msg.confidenceNote}
              draft={msg.draft}
              retryCount={msg.retryCount}
              chart={msg.chart}
              charts={msg.charts || []}
              displayMode="grade"
              sessionId={msg.sessionId}
              messageId={msg.requestId}
            />
          ))}

          {pendingQuestion && (
            <div
              className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed"
              style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
            >
              {pendingQuestion}
            </div>
          )}

          {loading && (
            <div className="self-start glass rounded-xl px-4 py-3 text-sm w-full max-w-md shadow-elevated">
              <ProgressPanel events={activeEvents} detailed={false} />
              {activeEvents.length === 0 && (
                <div className="flex items-center gap-2 text-muted-foreground text-xs">
                  <span className="inline-block w-3 h-3 border-2 border-[var(--border)] border-t-[var(--brand-blue)] rounded-full animate-spin" />
                  분석 준비 중…
                </div>
              )}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* 체크리스트 사이드패널 (데스크톱 전용) */}
      <aside className="hidden lg:block w-64 shrink-0 border-l border-[var(--border)] px-3 py-4 overflow-y-auto">
        <StartupChecklist
          items={checklistItems}
          progress={checklistProgress}
          onToggle={toggleItem}
        />
      </aside>
      </div>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-background border-t border-[var(--border)] max-w-5xl mx-auto w-full">
        {/* 모바일 전용 진행률 바 */}
        <div className="lg:hidden border-b border-[var(--border)] px-4 py-2">
          <ChecklistProgress progress={checklistProgress} total={8} />
        </div>

        {/* 샘플 질문 패널 */}
        {showSamples && (
          <div className="border-b border-[var(--border)] px-4 py-3 max-h-72 overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DOMAIN_CARDS.map(card => (
                <div
                  key={card.id}
                  className="rounded-xl p-3 border"
                  style={{ background: card.colorBg, borderColor: card.borderColor }}
                >
                  <div className="flex items-center gap-1.5 mb-2">
                    <span className="text-base">{card.icon}</span>
                    <span className="font-semibold text-xs text-foreground">{card.label}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    {card.questions.map(q => (
                      <button
                        key={q}
                        onClick={() => { setShowSamples(false); handleSubmit(q); }}
                        className="text-left text-xs px-2.5 py-1.5 rounded-lg transition-opacity hover:opacity-70 leading-relaxed"
                        style={{ background: "rgba(255,255,255,0.08)", color: "var(--foreground)" }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="px-4 py-3 flex flex-col gap-2">
          <button
            onClick={() => setShowSamples(v => !v)}
            className="self-start text-xs px-3 py-1.5 rounded-full border transition-colors"
            style={{
              borderColor: showSamples ? "var(--brand-blue)" : "var(--border)",
              color: showSamples ? "var(--brand-blue)" : "var(--muted-foreground)",
              background: showSamples ? "rgba(8,145,178,0.08)" : "transparent",
            }}
          >
            {showSamples ? "▲ 샘플 질문 닫기" : "💬 샘플 질문 보기"}
          </button>
          <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} defaultValue={placeholder} />
        </div>
      </footer>
    </div>
  );
}
