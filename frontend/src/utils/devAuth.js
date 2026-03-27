const SESSION_KEY = "sohobi_dev_auth";
const STORED_HASH = import.meta.env.VITE_DEV_PASSWORD_HASH ?? "";

export function isDevAuthenticated() {
  return sessionStorage.getItem(SESSION_KEY) === "1";
}

export function setDevAuthenticated() {
  sessionStorage.setItem(SESSION_KEY, "1");
}

export function clearDevAuth() {
  sessionStorage.removeItem(SESSION_KEY);
}

export async function checkDevPassword(input) {
  if (!STORED_HASH) return false;
  const encoded = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoded);
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return hashHex === STORED_HASH;
}
