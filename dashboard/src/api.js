// In development (localhost): use same host + port 5001 so browser allows the request.
// On Vercel/production: use VITE_API_URL if set, else PRODUCTION_API_URL so dashboard works without env var.
const API_PORT = 5001;
const PRODUCTION_API_URL = "https://shield-360-1.onrender.com";

function getBase() {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return `http://${host}:${API_PORT}`;
    return PRODUCTION_API_URL;
  }
  return `http://127.0.0.1:${API_PORT}`;
}

export async function fetchStats() {
  const res = await fetch(`${getBase()}/stats`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function fetchLogs({ limit = 200, status = "" } = {}) {
  const params = new URLSearchParams({ limit });
  if (status) params.set("status", status);
  const res = await fetch(`${getBase()}/logs?${params}`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function clearLogs() {
  const res = await fetch(`${getBase()}/logs/clear`, { method: "DELETE" });
  if (!res.ok) throw new Error("Clear failed");
  return res.json();
}

// --- Allowlist ---
export async function fetchAllowlist() {
  const res = await fetch(`${getBase()}/allowlist`);
  if (!res.ok) throw new Error("Server unreachable");
  return res.json();
}

export async function addAllowlist(domain, note = "") {
  const res = await fetch(`${getBase()}/allowlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, note }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to add");
  return data;
}

export async function removeAllowlist(id) {
  const res = await fetch(`${getBase()}/allowlist/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Remove failed");
  return res.json();
}
