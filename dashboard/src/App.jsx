import { useState, useEffect, useCallback } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import {
  fetchStats, fetchLogs, clearLogs,
  fetchAllowlist, addAllowlist, removeAllowlist,
} from "./api";
import "./App.css";

const STATUS_COLORS = {
  benign:          "#22c55e",
  phishing:        "#ef4444",
  malware:         "#f97316",
  defacement:      "#a855f7",
  company_allowed: "#38bdf8",
};

const STATUS_ICONS = {
  benign:          "✅",
  phishing:        "🎣",
  malware:         "☠️",
  defacement:      "🖤",
  company_allowed: "🏢",
};

function Badge({ status }) {
  const label = status === "company_allowed" ? "Safe – Company Allowed" : status;
  return (
    <span className="badge" style={{ backgroundColor: STATUS_COLORS[status] ?? "#64748b" }}>
      {STATUS_ICONS[status] ?? "❓"} {label}
    </span>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div className="stat-card" style={{ borderTop: `4px solid ${color}` }}>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function usePolling(fn, interval = 5000) {
  useEffect(() => {
    fn();
    const id = setInterval(fn, interval);
    return () => clearInterval(id);
  }, [fn, interval]);
}

// ── Allowlist Tab ─────────────────────────────────────────────────────────────
function AllowlistTab() {
  const [entries, setEntries]     = useState([]);
  const [domain, setDomain]       = useState("");
  const [note, setNote]           = useState("");
  const [error, setError]         = useState("");
  const [success, setSuccess]     = useState("");
  const [loading, setLoading]     = useState(false);

  const load = useCallback(async () => {
    try { setEntries(await fetchAllowlist()); } catch { /* server down */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    if (!domain.trim()) { setError("Please enter a domain."); return; }
    setLoading(true);
    try {
      const res = await addAllowlist(domain.trim(), note.trim());
      setSuccess(res.message);
      setDomain(""); setNote("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id, d) => {
    if (!window.confirm(`Remove "${d}" from allowlist?`)) return;
    await removeAllowlist(id);
    await load();
  };

  return (
    <section className="allowlist-section">
      <div className="allowlist-intro">
        <h2>🏢 Company Allowlist</h2>
        <p>
          Domains added here are always marked as{" "}
          <Badge status="company_allowed" /> regardless of what the AI detects.
          Useful for internal tools, partner sites, or regional services.
        </p>
      </div>

      {/* Add form */}
      <form className="allowlist-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="Domain (e.g. daraz.lk)"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
        />
        <input
          type="text"
          placeholder="Note / reason (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button type="submit" className="btn-add" disabled={loading}>
          {loading ? "Adding…" : "＋ Add to Allowlist"}
        </button>
      </form>

      {error   && <div className="msg msg-error">⚠️ {error}</div>}
      {success && <div className="msg msg-success">✅ {success}</div>}

      {/* Allowlist table */}
      <div className="table-wrap" style={{ marginTop: "1.25rem" }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Domain</th>
              <th>Note</th>
              <th>Added</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr><td colSpan={5} className="empty">No domains in the allowlist yet.</td></tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.id}</td>
                  <td className="domain-cell">🏢 {e.domain}</td>
                  <td style={{ color: "#94a3b8" }}>{e.note || "—"}</td>
                  <td>{new Date(e.added_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      className="btn-remove"
                      onClick={() => handleRemove(e.id, e.domain)}
                    >
                      🗑 Remove
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab]             = useState("dashboard");
  const [stats, setStats]         = useState(null);
  const [logs, setLogs]           = useState([]);
  const [filter, setFilter]       = useState("");
  const [serverDown, setServerDown] = useState(false);
  const [clearing, setClearing]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([fetchStats(), fetchLogs({ status: filter })]);
      setStats(s);
      setLogs(l);
      setServerDown(false);
      setLastRefresh(new Date());
    } catch {
      setServerDown(true);
    }
  }, [filter]);

  usePolling(refresh, 5000);

  const handleClear = async () => {
    if (!window.confirm("Clear all scan logs?")) return;
    setClearing(true);
    await clearLogs();
    await refresh();
    setClearing(false);
  };

  const pieData = stats
    ? Object.entries(stats.breakdown).map(([name, value]) => ({ name, value }))
    : [];

  const barData = stats
    ? Object.entries(stats.breakdown).map(([name, value]) => ({ name, count: value }))
    : [];

  const threats = stats
    ? (stats.breakdown.phishing    ?? 0) +
      (stats.breakdown.malware     ?? 0) +
      (stats.breakdown.defacement  ?? 0)
    : 0;

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div className="header-left">
          <span className="logo">🛡️ Shield360</span>
          <span className="subtitle">Shadow IT & Asset Visibility Dashboard</span>
        </div>
        <div className="header-right">
          {serverDown ? (
            <span className="pill pill-danger">⚠️ Server Offline</span>
          ) : (
            <span className="pill pill-ok">● Live</span>
          )}
          {lastRefresh && (
            <span className="last-refresh">Updated {lastRefresh.toLocaleTimeString()}</span>
          )}
        </div>
      </header>

      {serverDown && (
        <div className="banner-error">
          Cannot reach Shield360 API at http://127.0.0.1:5000 — make sure{" "}
          <code>python app.py</code> is running.
        </div>
      )}

      {/* TAB NAV */}
      <nav className="tab-nav">
        <button
          className={tab === "dashboard" ? "tab-btn active" : "tab-btn"}
          onClick={() => setTab("dashboard")}
        >
          📊 Dashboard
        </button>
        <button
          className={tab === "allowlist" ? "tab-btn active" : "tab-btn"}
          onClick={() => setTab("allowlist")}
        >
          🏢 Company Allowlist
        </button>
      </nav>

      {/* ── DASHBOARD TAB ── */}
      {tab === "dashboard" && (
        <>
          <section className="cards">
            <StatCard label="Total Scanned"     value={stats?.total ?? "—"}                    color="#38bdf8" />
            <StatCard label="Threats Found"     value={threats || "—"}                         color="#ef4444" />
            <StatCard label="Phishing"          value={stats?.breakdown?.phishing    ?? 0}     color="#ef4444" />
            <StatCard label="Malware"           value={stats?.breakdown?.malware     ?? 0}     color="#f97316" />
            <StatCard label="Defacement"        value={stats?.breakdown?.defacement  ?? 0}     color="#a855f7" />
            <StatCard label="Company Allowed"   value={stats?.breakdown?.company_allowed ?? 0} color="#38bdf8" />
          </section>

          <section className="charts">
            <div className="chart-card">
              <h3>Threat Breakdown</h3>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? "#64748b"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Scans by Category</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {barData.map((entry) => (
                      <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? "#64748b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card recent-threats">
              <h3>Recent Threats</h3>
              {(stats?.recent_threats ?? []).length === 0 ? (
                <p className="empty">No threats detected yet.</p>
              ) : (
                <ul className="threat-list">
                  {(stats?.recent_threats ?? []).map((t) => (
                    <li key={t.id}>
                      <Badge status={t.status} />
                      <span className="threat-url" title={t.url}>{t.url}</span>
                      <span className="threat-conf">{(t.confidence * 100).toFixed(0)}%</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="log-section">
            <div className="log-header">
              <h3>Scan Log</h3>
              <div className="log-controls">
                <select value={filter} onChange={(e) => setFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="benign">Benign</option>
                  <option value="phishing">Phishing</option>
                  <option value="malware">Malware</option>
                  <option value="defacement">Defacement</option>
                  <option value="company_allowed">Company Allowed</option>
                </select>
                <button className="btn-clear" onClick={handleClear} disabled={clearing}>
                  {clearing ? "Clearing…" : "🗑 Clear Logs"}
                </button>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Timestamp</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>URL</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr><td colSpan={5} className="empty">No scans recorded yet.</td></tr>
                  ) : (
                    logs.map((row) => (
                      <tr
                        key={row.id}
                        className={
                          row.status === "company_allowed" ? "row-allowed"
                          : row.status !== "benign" ? "row-threat"
                          : ""
                        }
                      >
                        <td>{row.id}</td>
                        <td>{new Date(row.scanned_at).toLocaleString()}</td>
                        <td><Badge status={row.status} /></td>
                        <td>{(row.confidence * 100).toFixed(1)}%</td>
                        <td className="url-cell" title={row.url}>{row.url}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {/* ── ALLOWLIST TAB ── */}
      {tab === "allowlist" && <AllowlistTab />}
    </div>
  );
}
