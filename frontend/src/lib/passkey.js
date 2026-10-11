/**
 * passkey.js — WebAuthn ceremonies for the FREK-ID passkey (C1).
 * Options come from FREKCORE through Laurent.ia (base64url JSON); the browser's
 * authenticator signs; the result goes back as base64url JSON. No third party.
 */
const API = `${process.env.REACT_APP_BACKEND_URL}/api/auth/passkey`;

const b64urlToBuf = (s) => {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0)).buffer;
};
const bufToB64url = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function post(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Erreur ${r.status}`);
  return data;
}

export const passkeySupported = () => typeof window !== "undefined" && !!window.PublicKeyCredential;

export async function registerPasskey(frekId, enrollmentToken) {
  // enrollment_lock: this ceremony's exclusive reservation; only it can complete.
  const { enrollment_lock: enrollmentLock, ...o } = await post("/register/begin", {
    frek_id: frekId,
    enrollment_token: enrollmentToken,
  });
  const cred = await navigator.credentials.create({
    publicKey: {
      ...o,
      challenge: b64urlToBuf(o.challenge),
      user: { ...o.user, id: b64urlToBuf(o.user.id) },
      excludeCredentials: (o.excludeCredentials || []).map((c) => ({ ...c, id: b64urlToBuf(c.id) })),
    },
  });
  return post("/register/complete", {
    frek_id: frekId,
    enrollment_token: enrollmentToken,
    enrollment_lock: enrollmentLock,
    credential: {
      id: cred.id,
      rawId: bufToB64url(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufToB64url(cred.response.clientDataJSON),
        attestationObject: bufToB64url(cred.response.attestationObject),
        transports: cred.response.getTransports ? cred.response.getTransports() : [],
      },
      clientExtensionResults: cred.getClientExtensionResults(),
      authenticatorAttachment: cred.authenticatorAttachment || null,
    },
  });
}

export async function loginWithPasskey(frekId) {
  const o = await post("/login/begin", { frek_id: frekId });
  const cred = await navigator.credentials.get({
    publicKey: {
      ...o,
      challenge: b64urlToBuf(o.challenge),
      allowCredentials: (o.allowCredentials || []).map((c) => ({ ...c, id: b64urlToBuf(c.id) })),
    },
  });
  return post("/login/complete", {
    frek_id: frekId,
    credential: {
      id: cred.id,
      rawId: bufToB64url(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufToB64url(cred.response.clientDataJSON),
        authenticatorData: bufToB64url(cred.response.authenticatorData),
        signature: bufToB64url(cred.response.signature),
        userHandle: cred.response.userHandle ? bufToB64url(cred.response.userHandle) : null,
      },
      clientExtensionResults: cred.getClientExtensionResults(),
      authenticatorAttachment: cred.authenticatorAttachment || null,
    },
  });
}
