/**
 * api.js: EVERY call to the backend lives here.
 * Pages never use fetch() directly; they call these functions.
 * If an endpoint changes, you fix it in one place.
 */
import { buildEligibilityCheckPayload } from "./eligibilityRequests.js";

// Empty in development (Vite proxies /api to localhost:8000). In production, set VITE_API_BASE
// to the deployed backend address, e.g. https://nagrikai-api.onrender.com (no trailing slash).
const API_BASE = (import.meta.env?.VITE_API_BASE || "").replace(/\/$/, "");

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the NagrikAI server. It may be waking up (wait 1 minute and retry) or offline.");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }
  return res.json();
}

const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body) });

/** Health check (also tells us which backend version is running) */
export const getHealth = () => request("/api/health");

/** Policy Explorer */
export function searchPolicies(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v && qs.set(k, v));
  return request(`/api/policies/search?${qs}`);
}
export const addPolicyFromUrl = (url) => post("/api/policies/from-url", { url });
/** Upload a PDF from the user's computer: the file itself is the request body. */
export const uploadPolicyPdf = (file) =>
  request(`/api/policies/upload?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: { "Content-Type": "application/pdf" },
    body: file,
  });
export const getPolicy = (id) => request(`/api/policies/${id}`);
export const getDocument = (id) => request(`/api/policies/${id}/document`);

/** Policy Explainer */
export const explainPolicy = (policy_id, language = "en", refresh = false) =>
  post("/api/explain", { policy_id, language, refresh });
export const askPolicy = (policy_id, question, language = "en") =>
  post("/api/ask", { policy_id, question, language });

/** Eligibility Checker */
export const getRules = (policy_id) => post("/api/eligibility/rules", { policy_id });
export const checkEligibility = (policy_id, profile, language = "en", answers = {}, follow_up_submitted = false) =>
  post("/api/eligibility/check", buildEligibilityCheckPayload(policy_id, profile, language, answers, follow_up_submitted));

