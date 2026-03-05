// In development: uses http://127.0.0.1:5000
// In production: set VITE_API_URL in Vercel environment variables
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

export async function fetchStats() {
  const res = await fetch(`${BASE}/stats`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function fetchLogs({ limit = 200, status = "" } = {}) {
  const params = new URLSearchParams({ limit });
  if (status) params.set("status", status);
  const res = await fetch(`${BASE}/logs?${params}`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function clearLogs() {
  const res = await fetch(`${BASE}/logs/clear`, { method: "DELETE" });
  if (!res.ok) throw new Error("Clear failed");
  return res.json();
}

// --- Allowlist ---
export async function fetchAllowlist() {
  const res = await fetch(`${BASE}/allowlist`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function addAllowlist(domain, note = "") {
  const res = await fetch(`${BASE}/allowlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, note }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to add");
  return data;
}

export async function removeAllowlist(id) {
  const res = await fetch(`${BASE}/allowlist/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Remove failed");
  return res.json();
}
