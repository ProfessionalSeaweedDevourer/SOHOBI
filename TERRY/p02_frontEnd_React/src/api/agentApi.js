const AGENT_URL = "/agent";

export async function sendChatMessage(question, sessionId = null, admCd = null) {
  const body = {
    question,
    session_id: sessionId,
  };
  if (admCd) body.adm_cd = admCd;

  const res = await fetch(`${AGENT_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
