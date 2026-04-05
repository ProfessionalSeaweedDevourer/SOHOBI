const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const _HEADERS = {
  'Content-Type': 'application/json',
  ...(import.meta.env.VITE_API_KEY ? { 'X-API-Key': import.meta.env.VITE_API_KEY } : {}),
};

/**
 * 사용 이벤트를 백엔드로 전송한다.
 * 전송 실패 시 무시 — UX 영향 없음.
 *
 * @param {string} eventName  - 이벤트 이름 (agent_query, agent_response_view, feature_discovery)
 * @param {object} payload    - 이벤트 추가 데이터
 */
export async function trackEvent(eventName, payload = {}) {
  try {
    await fetch(`${BASE_URL}/api/events`, {
      method: 'POST',
      headers: _HEADERS,
      body: JSON.stringify({
        event_name: eventName,
        ...payload,
        timestamp: new Date().toISOString(),
      }),
    });
  } catch {
    // 실패 무시
  }
}
