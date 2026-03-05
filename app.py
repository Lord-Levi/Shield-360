"""
Shield360 API Server — Shadow IT & Asset Visibility Engine
Lightweight local backend that connects the Chrome Extension to the ML model.
"""
from pathlib import Path
import sqlite3
import threading
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "model.pkl"
VECTORIZER_FILE = BASE_DIR / "vectorizer.pkl"
DB_FILE = BASE_DIR / "shield360.db"
DEFAULT_PORT = 5000

app = Flask(__name__)
CORS(app)

# --- DATABASE SETUP ---
db_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT    NOT NULL,
                status     TEXT    NOT NULL,
                confidence REAL    NOT NULL,
                scanned_at TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS allowlist (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                domain     TEXT    NOT NULL UNIQUE,
                note       TEXT    NOT NULL DEFAULT '',
                added_at   TEXT    NOT NULL
            )
        """)
        conn.commit()

init_db()

def log_scan(url: str, status: str, confidence: float):
    ts = datetime.now(timezone.utc).isoformat()
    with db_lock:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO scans (url, status, confidence, scanned_at) VALUES (?, ?, ?, ?)",
                (url, status, round(confidence, 4), ts)
            )
            conn.commit()

def extract_domain(url: str) -> str:
    """Return bare domain (host without port) from a URL string."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.netloc or parsed.path).lower()
        return host.split("@")[-1].split(":")[0]
    except Exception:
        return ""

def is_allowlisted(url: str) -> bool:
    """Check if the URL's domain (or any parent domain) is in the allowlist."""
    domain = extract_domain(url)
    if not domain:
        return False
    parts = domain.split(".")
    # Check full domain and progressively shorter parent domains
    candidates = [".".join(parts[i:]) for i in range(len(parts))]
    with get_db() as conn:
        placeholders = ",".join("?" * len(candidates))
        row = conn.execute(
            f"SELECT 1 FROM allowlist WHERE domain IN ({placeholders}) LIMIT 1",
            candidates
        ).fetchone()
    return row is not None


# --- CUSTOM TOKENIZER (must match training) ---
def make_tokens(f):
    tokens_by_slash = str(f).split("/")
    total_tokens = []
    for i in tokens_by_slash:
        tokens = str(i).split("-")
        tokens_dot = []
        for j in tokens:
            temp_tokens = str(j).split(".")
            tokens_dot = tokens_dot + temp_tokens
        total_tokens = total_tokens + tokens + tokens_dot
    total_tokens = list(set(total_tokens))
    # Remove noise tokens that carry no meaningful signal
    for noise in ("com", "www", "https:", "http:", ""):
        if noise in total_tokens:
            total_tokens.remove(noise)
    return total_tokens


# --- LOAD ML MODEL ---
model = None
vectorizer = None

def load_model():
    global model, vectorizer
    try:
        with open(VECTORIZER_FILE, "rb") as f:
            vectorizer = pickle.load(f)
        with open(MODEL_FILE, "rb") as f:
            model = pickle.load(f)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[ERROR] Model load failed: {e}")
        return False

if not load_model():
    print("[WARN] Model files not found. Run shield360_engine.py (Option 1) to train.")
else:
    print("✅ Shield360 Server ready — model loaded successfully")

# --- CONFIDENCE THRESHOLD ---
# Only flag as threat when model confidence is >= this value; otherwise treat as benign
CONFIDENCE_THRESHOLD = 0.70


# --- API ENDPOINTS ---

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "service": "Shield360",
    })


@app.route("/scan", methods=["POST"])
def scan():
    """
    Scan a URL for threats.
    Body: { "url": "https://..." }
    Returns: { "url", "status", "confidence" }
    """
    if model is None or vectorizer is None:
        return jsonify({"error": "Model not loaded"}), 503

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Company allowlist check — overrides the ML result entirely
    if is_allowlisted(url):
        log_scan(url, "company_allowed", 1.0)
        result = {"url": url, "status": "company_allowed", "confidence": 1.0}
        print(f"✅ {url[:70]} → company_allowed")
        return jsonify(result)

    try:
        url_vector = vectorizer.transform([url])
        probabilities = model.predict_proba(url_vector)[0]
        confidence = float(np.max(probabilities))
        prediction = model.classes_[int(np.argmax(probabilities))]
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return jsonify({"error": "Prediction failed", "url": url}), 500

    status = "benign" if (confidence < CONFIDENCE_THRESHOLD or prediction == "benign") else prediction

    log_scan(url, status, confidence)

    result = {"url": url, "status": status, "confidence": round(confidence, 4)}
    print(f"🔍 {url[:70]} → {status} ({confidence:.0%})")
    return jsonify(result)


@app.route("/logs", methods=["GET"])
def logs():
    """
    Return scan history for the dashboard.
    Query params:
      limit  (int, default 200)  — max rows to return
      status (str, optional)     — filter by status
    """
    limit = min(int(request.args.get("limit", 200)), 1000)
    status_filter = request.args.get("status", "").strip().lower()

    with get_db() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM scans WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status_filter, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scans ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()

    return jsonify([dict(r) for r in rows])


@app.route("/stats", methods=["GET"])
def stats():
    """Summary counts per status — used by dashboard charts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM scans GROUP BY status"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        recent_threats = conn.execute(
            """SELECT * FROM scans WHERE status != 'benign'
               ORDER BY id DESC LIMIT 5"""
        ).fetchall()

    return jsonify({
        "total": total,
        "breakdown": {r["status"]: r["count"] for r in rows},
        "recent_threats": [dict(r) for r in recent_threats],
    })


@app.route("/allowlist", methods=["GET"])
def get_allowlist():
    """Return all company-allowed domains."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM allowlist ORDER BY added_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/allowlist", methods=["POST"])
def add_allowlist():
    """
    Add a domain to the company allowlist.
    Body: { "domain": "daraz.lk", "note": "Internal tool" }
    """
    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "").strip().lower()
    note = data.get("note", "").strip()

    if not domain:
        return jsonify({"error": "No domain provided"}), 400

    # Strip protocol/path — store bare domain only
    domain = extract_domain(domain) or domain

    ts = datetime.now(timezone.utc).isoformat()
    try:
        with db_lock:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO allowlist (domain, note, added_at) VALUES (?, ?, ?)",
                    (domain, note, ts)
                )
                conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": f"'{domain}' is already in the allowlist"}), 409

    print(f"✅ Allowlisted: {domain}")
    return jsonify({"message": f"'{domain}' added to company allowlist.", "domain": domain}), 201


@app.route("/allowlist/<int:entry_id>", methods=["DELETE"])
def remove_allowlist(entry_id):
    """Remove a domain from the company allowlist by its ID."""
    with db_lock:
        with get_db() as conn:
            row = conn.execute(
                "SELECT domain FROM allowlist WHERE id = ?", (entry_id,)
            ).fetchone()
            if not row:
                return jsonify({"error": "Entry not found"}), 404
            conn.execute("DELETE FROM allowlist WHERE id = ?", (entry_id,))
            conn.commit()

    print(f"🗑 Removed from allowlist: {row['domain']}")
    return jsonify({"message": f"'{row['domain']}' removed from allowlist."})


@app.route("/logs/clear", methods=["DELETE"])
def clear_logs():
    """Wipe all scan history."""
    with db_lock:
        with get_db() as conn:
            conn.execute("DELETE FROM scans")
            conn.commit()
    return jsonify({"message": "All logs cleared."})


# --- ENTRY POINT ---
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", os.environ.get("SHIELD360_PORT", DEFAULT_PORT)))
    # Use 0.0.0.0 in production (cloud) and 127.0.0.1 locally
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    app.run(host=host, port=port, threaded=True)
