/**
 * 백엔드 오류 메시지를 일반 사용자에게 친화적인 한국어 설명으로 변환.
 */
export function interpretError(msg) {
  if (!msg) return "오류가 발생했습니다.";
  const m = msg.toLowerCase();

  if (m.includes("content_filter") || m.includes("content filter"))
    return "콘텐츠 정책에 의해 처리할 수 없는 질문입니다. 표현을 바꿔 다시 시도해 주세요.";

  if (m.includes("429") || m.includes("rate limit") || m.includes("too many"))
    return "요청이 너무 많습니다. 잠시 후(30초~1분) 다시 시도해 주세요.";

  if (/http 5\d{2}/.test(m) || m.includes("server error") || m.includes("internal"))
    return "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";

  if (
    m.includes("'str'") || m.includes("'int'") ||
    m.includes("unsupported operand") || m.includes("argument must be")
  )
    return "데이터 처리 중 형식 오류가 발생했습니다. 지역명 또는 수치를 정확히 입력해 주세요.";

  if (m.includes("빈 응답") || m.includes("empty"))
    return "AI가 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.";

  if (m.includes("재무 시뮬레이션") || m.includes("수치가 질문에 포함"))
    return "재무 시뮬레이션을 위해 예상 매출·재료비·인건비 등 구체적인 금액을 포함해 주세요.";

  if (m.includes("timeout") || m.includes("network") || m.includes("fetch"))
    return "연결에 실패했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.";

  return `오류가 발생했습니다: ${msg}`;
}
