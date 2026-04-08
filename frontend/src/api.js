// SWA 프록시 사용 시 VITE_API_URL을 빈 문자열로 설정하면 상대경로(/api/...)로 동작한다.
// 로컬 개발 시 VITE_API_URL=http://localhost:8000 으로 설정한다.
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _AUTH_HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

function fetchWithTimeout(url, options = {}, ms = 15000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { ...options, signal: ctrl.signal }).finally(() => clearTimeout(id));
}

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
  const res = await fetchWithTimeout(`${BASE_URL}/api/v1/query`, {
    method: "POST",
    headers: _AUTH_HEADERS,
    body: JSON.stringify(body),
  }, 30000);
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
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
export async function streamQuery(question, maxRetries = 3, sessionId = null, onEvent, currentParams = null, signal = null) {
  const body = { question, domain: null, max_retries: maxRetries };
  if (sessionId) body.session_id = sessionId;
  if (currentParams) body.current_params = currentParams;

  const res = await fetch(`${BASE_URL}/api/v1/stream`, {
    method: "POST",
    headers: _AUTH_HEADERS,
    body: JSON.stringify(body),
    ...(signal ? { signal } : {}),
  });
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";
  let currentDataLines = [];

  while (true) {
    if (signal?.aborted) { reader.cancel(); break; }
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
 * @param {string} userId  특정 사용자만 필터링 (빈 문자열이면 전체)
 * @returns {Promise<{type, count, entries: Array}>}
 */
export async function fetchLogs(type = "queries", limit = 500, userId = "") {
  const params = new URLSearchParams({ type, limit });
  if (userId) params.append("user_id", userId);
  const res = await fetchWithTimeout(
    `${BASE_URL}/api/v1/logs?${params}`,
    { headers: _AUTH_HEADERS }
  );
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/v1/stats — 성능 통계 집계
 * @param {number} hours 조회 기간 (1-168)
 */
export async function fetchStats(hours = 24) {
  const params = new URLSearchParams({ hours });
  const res = await fetchWithTimeout(
    `${BASE_URL}/api/v1/stats?${params}`,
    { headers: _AUTH_HEADERS }
  );
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/v1/logs/users — 로그에 등장한 사용자 목록 (드롭다운용)
 * @returns {Promise<{count: number, users: Array<{user_id, email, name}>}>}
 */
export async function fetchLogUsers() {
  const res = await fetchWithTimeout(`${BASE_URL}/api/v1/logs/users`, { headers: _AUTH_HEADERS });
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/roadmap/votes
 * @returns {Promise<{features: Array<{feature_id, label, icon, vote_count, user_voted}>}>}
 */
export async function fetchRoadmapVotes() {
  const res = await fetchWithTimeout(`${BASE_URL}/api/roadmap/votes`, { headers: _AUTH_HEADERS });
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/feedback
 * @param {number} limit
 * @returns {Promise<{count: number, items: Array}>}
 */
export async function fetchFeedback(limit = 500) {
  const res = await fetchWithTimeout(
    `${BASE_URL}/api/feedback?limit=${limit}`,
    { headers: _AUTH_HEADERS }
  );
  if (!res.ok) {
    const text = await res.text();
    let err = {};
    try { err = JSON.parse(text); } catch {}
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}
