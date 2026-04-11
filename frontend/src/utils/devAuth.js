const SESSION_KEY = "sohobi_dev_auth";
const SESSION_NONCE_KEY = "sohobi_dev_nonce";
const STORED_HASH = import.meta.env.VITE_DEV_PASSWORD_HASH ?? "";

function hexToBytes(hex) {
  return new Uint8Array(hex.match(/.{2}/g).map((b) => parseInt(b, 16)));
}

function bytesToHex(bytes) {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function isDevAuthenticated() {
  const nonceHex = sessionStorage.getItem(SESSION_NONCE_KEY);
  const storedToken = sessionStorage.getItem(SESSION_KEY);
  if (!nonceHex || !storedToken || !STORED_HASH) return false;

  try {
    const hashBytes = hexToBytes(STORED_HASH);
    const key = await crypto.subtle.importKey(
      "raw",
      hashBytes,
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );
    const nonce = hexToBytes(nonceHex);
    const tokenBytes = hexToBytes(storedToken);
    return await crypto.subtle.verify("HMAC", key, tokenBytes, nonce);
  } catch {
    return false;
  }
}

export async function setDevAuthenticated(hashHex) {
  const nonce = crypto.getRandomValues(new Uint8Array(16));
  const hashBytes = hexToBytes(hashHex);
  const key = await crypto.subtle.importKey(
    "raw",
    hashBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const tokenBuffer = await crypto.subtle.sign("HMAC", key, nonce);
  sessionStorage.setItem(SESSION_NONCE_KEY, bytesToHex(nonce));
  sessionStorage.setItem(SESSION_KEY, bytesToHex(new Uint8Array(tokenBuffer)));
}

export function clearDevAuth() {
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(SESSION_NONCE_KEY);
}

export async function checkDevPassword(input) {
  if (!STORED_HASH) return { ok: false, hash: "" };
  const encoded = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoded);
  const hashHex = bytesToHex(new Uint8Array(hashBuffer));
  return { ok: hashHex === STORED_HASH, hash: hashHex };
}
