// SWA 프록시 사용 시 VITE_API_URL을 빈 문자열로 설정하면 상대경로(/api/...)로 동작한다.
// 로컬 개발 시 VITE_API_URL=http://localhost:8000 으로 설정한다.
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _AUTH_HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

/**
 * POST /api/v1/query
 * @param {string} question
 * @param {number} maxRetries
 * @param {string|null} sessionId  기존 세션 이어가기 (null이면 서버가 새 UUID 발급)
 * @returns {Promise<{session_id, request_id, status, grade, confidence_note,
 *   domain, draft, retry_count, agent_ms, signoff_ms, message, rejection_history?}>}
 */
export async function sendQuery(question, maxRetries = 3, sessionId = null, currentParams = null) {
  const body = { question, domain: null, max_retries: maxRetries };
  if (sessionId) body.session_id = sessionId;
  if (currentParams) body.current_params = currentParams;
  const res = await fetch(`${BASE_URL}/api/v1/query`, {
    method: "POST",
    headers: _AUTH_HEADERS,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * POST /api/v1/stream  — SSE 스트리밍
 * @param {string} question
 * @param {number} maxRetries
 * @param {string|null} sessionId
 * @param {(eventName: string, data: object) => void} onEvent  이벤트 콜백
 * @returns {Promise<void>}  스트림 종료 시 resolve
 */
export async function streamQuery(question, maxRetries = 3, sessionId = null, onEvent, currentParams = null) {
  const body = { question, domain: null, max_retries: maxRetries };
  if (sessionId) body.session_id = sessionId;
  if (currentParams) body.current_params = currentParams;

  const res = await fetch(`${BASE_URL}/api/v1/stream`, {
    method: "POST",
    headers: _AUTH_HEADERS,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";
  let currentDataLines = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // 마지막 불완전 줄은 버퍼에 보존

    for (const line of lines) {
      if (line === "") {
        // 빈 줄 = 이벤트 경계
        if (currentDataLines.length > 0) {
          try {
            const data = JSON.parse(currentDataLines.join("\n"));
            onEvent(currentEvent, data);
          } catch (_) { /* ignore */ }
        }
        currentEvent = "message";
        currentDataLines = [];
      } else if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        currentDataLines.push(line.slice(5).trim());
      }
    }
  }
}

/**
 * GET /api/v1/logs
 * @param {"queries"|"rejections"} type
 * @param {number} limit
 * @returns {Promise<{type, count, entries: Array}>}
 */
export async function fetchLogs(type = "queries", limit = 500) {
  const res = await fetch(
    `${BASE_URL}/api/v1/logs?type=${type}&limit=${limit}`,
    { headers: _AUTH_HEADERS }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}
