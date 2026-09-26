/**
 * Network calls to the LegalLens API. Every failure becomes an Error with a user-friendly message.
 */

export const SERVER_HINT =
  "Open LegalLens from its server address (for example http://localhost:8000), not the HTML file directly.";
export const NETWORK_ERROR = `Could not reach the LegalLens server. ${SERVER_HINT}`;

export function isJson(response) {
  return (response.headers.get("content-type") || "").includes("application/json");
}

/** Limits and mode from GET /api/config. */
export async function fetchConfig() {
  let response;
  try {
    response = await fetch("/api/config");
  } catch {
    throw new Error(NETWORK_ERROR);
  }
  if (!response.ok || !isJson(response)) throw new Error(NETWORK_ERROR);
  return response.json();
}

/** POST to a brief endpoint and return the brief, or throw an Error with the server's friendly message. */
export async function postBrief(url, body) {
  let response;
  try {
    response = await fetch(url, { method: "POST", body });
  } catch {
    throw new Error(NETWORK_ERROR);
  }
  if (!isJson(response)) {
    throw new Error(`Unexpected response from the server (HTTP ${response.status}). ${SERVER_HINT}`);
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (HTTP ${response.status}).`);
  }
  return data;
}
