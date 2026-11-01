/**
 * recent.js: "Recently viewed" policies, kept in the browser's localStorage.
 * This is the user's own history (not data from the backend).
 */
const KEY = "recentPolicies";

export function getRecent() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || [];
  } catch {
    return [];
  }
}

export function clearRecent() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* storage blocked: ignore */
  }
}

export function addRecent(policy) {
  try {
    const next = [
      { id: policy.id, title: policy.title, authority: policy.authority, source: policy.source },
      ...getRecent().filter((p) => p.id !== policy.id),
    ].slice(0, 8);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage blocked: ignore */
  }
}
