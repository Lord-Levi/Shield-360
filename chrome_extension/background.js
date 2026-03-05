/**
 * Shield360 Chrome Extension - Background Service Worker
 * Captures URLs when pages finish loading and sends them to the local ML server.
 * Triggers native notifications when threats are detected.
 */

// Change this to your Render URL after deployment
// e.g. "https://shield360-api.onrender.com"
// For local use: "http://127.0.0.1:5000"
const SHIELD360_SERVER = "http://127.0.0.1:5000";
const SCAN_ENDPOINT = `${SHIELD360_SERVER}/scan`;
const RECENT_SCANS_MS = 5000; // Debounce: skip re-scanning same URL within 5s

const recentUrls = new Map(); // url -> timestamp

function shouldScan(url) {
  if (!url || typeof url !== "string") return false;
  const u = url.trim().toLowerCase();
  // Skip browser internal pages
  if (
    u.startsWith("chrome://") ||
    u.startsWith("chrome-extension://") ||
    u.startsWith("edge://") ||
    u.startsWith("about:") ||
    u.startsWith("moz-extension://")
  ) {
    return false;
  }
  // Debounce: avoid re-scanning same URL in quick succession
  const now = Date.now();
  const last = recentUrls.get(u);
  if (last && now - last < RECENT_SCANS_MS) return false;
  recentUrls.set(u, now);
  // Prune old entries
  if (recentUrls.size > 500) {
    const cutoff = now - RECENT_SCANS_MS * 2;
    for (const [key, ts] of recentUrls.entries()) {
      if (ts < cutoff) recentUrls.delete(key);
    }
  }
  return true;
}

async function analyzeUrl(url) {
  if (!shouldScan(url)) return;
  try {
    const res = await fetch(SCAN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    if (data.status && data.status !== "benign") {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icon48.png",
        title: "⚠️ Shield360 Security Alert",
        message: `DANGER: This site is detected as ${data.status.toUpperCase()}!`,
        priority: 2,
      });
    }
  } catch (err) {
    // Server may be offline; fail silently to avoid spamming user
    console.debug("[Shield360] Server unreachable:", err.message);
  }
}

// Fire when the main frame has finished loading (webNavigation API)
chrome.webNavigation.onCompleted.addListener(
  (details) => {
    if (details.frameId === 0) {
      analyzeUrl(details.url);
    }
  },
  { url: [{ schemes: ["http", "https"] }] }
);

// Fallback: also listen to tab updates (e.g. for edge cases)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab?.url?.startsWith("http")) {
    analyzeUrl(tab.url);
  }
});
