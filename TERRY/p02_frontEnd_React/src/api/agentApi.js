const AGENT_URL = "/agent";

export async function sendChatMessage(question, sessionId = null) {
  const res = await fetch(`${AGENT_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  });
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json();
}

export async function getLocations() {
  const res = await fetch(`${AGENT_URL}/locations`);
  return res.json();
}

export async function getIndustries() {
  const res = await fetch(`${AGENT_URL}/industries`);
  return res.json();
}
