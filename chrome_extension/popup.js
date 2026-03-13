/**
 * Shield360 popup — "Scan this page" button.
 * Must match SHIELD360_SERVER in background.js.
 */
const SHIELD360_SERVER = "https://shield-360-1.onrender.com";
const SCAN_ENDPOINT = `${SHIELD360_SERVER}/scan`;

const scanBtn = document.getElementById("scanBtn");
const resultEl = document.getElementById("result");

function setResult(html, className) {
  resultEl.innerHTML = html;
  resultEl.className = "visible " + (className || "");
}

function showError(message) {
  setResult(`<span class="status">Error</span><br>${message}`, "error");
}

scanBtn.addEventListener("click", async () => {
  scanBtn.disabled = true;
  setResult("<span class="status">Scanning…</span>", "safe");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) {
      showError("No page to scan.");
      scanBtn.disabled = false;
      return;
    }
    const url = tab.url;
    if (url.startsWith("chrome://") || url.startsWith("chrome-extension://") || url.startsWith("edge://") || url.startsWith("about:")) {
      showError("Cannot scan browser internal pages.");
      scanBtn.disabled = false;
      return;
    }

    const res = await fetch(SCAN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Scan request failed.");
      scanBtn.disabled = false;
      return;
    }

    const status = data.status || "unknown";
    const confidence = data.confidence != null ? Math.round(data.confidence * 100) + "%" : "—";
    const shortUrl = (url.length > 50 ? url.slice(0, 47) + "…" : url)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

    let className = "safe";
    let label = "Safe";
    if (status === "company_allowed") {
      className = "allowed";
      label = "Company allowed";
    } else if (status !== "benign") {
      className = "threat";
      label = status.charAt(0).toUpperCase() + status.slice(1);
    }

    setResult(
      `<span class="status">${label}</span> (${confidence})<div class="url">${shortUrl}</div>`,
      className
    );
  } catch (err) {
    showError("Cannot reach Shield360 API. Check your connection or that the server is running.");
  }

  scanBtn.disabled = false;
});
