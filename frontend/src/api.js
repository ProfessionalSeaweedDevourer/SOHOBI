const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * POST /api/v1/query
 * @param {string} question
 * @param {number} maxRetries
 * @returns {Promise<{request_id, status, domain, draft, retry_count, message, rejection_history?}>}
 */
export async function sendQuery(question, maxRetries = 3) {
  const res = await fetch(`${BASE_URL}/api/v1/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, domain: null, max_retries: maxRetries }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/v1/logs
 * @param {"queries"|"rejections"} type
 * @param {number} limit
 * @returns {Promise<{type, count, entries: Array}>}
 */
export async function fetchLogs(type = "queries", limit = 50) {
  const res = await fetch(
    `${BASE_URL}/api/v1/logs?type=${type}&limit=${limit}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}
