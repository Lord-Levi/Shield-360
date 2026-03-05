# Shield360 — Shadow IT & Asset Visibility Engine

A cybersecurity product for Small and Medium Enterprises (SMEs) that detects phishing, malware, and defacement threats in real-time via a Chrome Extension, a local ML engine, and a live admin dashboard.

---

## Project Structure

```
Shield360_Project/
├── app.py                  # Flask API server
├── shield360_engine.py     # ML model training script
├── app_gui.py              # Legacy manual test GUI
├── requirements.txt        # Python dependencies
├── render.yaml             # Render.com deployment config
├── chrome_extension/       # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js
│   ├── icon48.png
│   └── icon128.png
└── dashboard/              # React admin dashboard (Vite)
    └── src/
        ├── App.jsx
        ├── App.css
        └── api.js
```

---

## Local Setup

### 1. Install Python dependencies
```bash
cd Shield360_Project
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Train the ML model
Place `malicious_phish.csv` in the project root, then run:
```bash
python shield360_engine.py
# Choose Option 1
```
This generates `model.pkl` and `vectorizer.pkl`.

### 3. Start the API server
```bash
python app.py
# Runs at http://127.0.0.1:5000
```

### 4. Start the dashboard
```bash
cd dashboard
npm install
npm run dev
# Opens at http://localhost:5173
```

### 5. Load the Chrome Extension
1. Open Chrome → `chrome://extensions/`
2. Enable **Developer Mode**
3. Click **Load unpacked** → select the `chrome_extension/` folder

---

## Production Deployment

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial Shield360 commit"
git remote add origin https://github.com/YOUR_USERNAME/shield360.git
git push -u origin main
```

> **Important:** `model.pkl`, `vectorizer.pkl`, `malicious_phish.csv`, and `shield360.db` are excluded by `.gitignore` because they are large binary/data files. Upload `model.pkl` and `vectorizer.pkl` manually as **GitHub Release assets** after creating a release, then download them to the Render server.

---

### Step 2 — Deploy Backend on Render.com

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Click **Deploy**
6. Your API will be live at: `https://shield360-api.onrender.com`

> **Model files on Render:** After first deploy, go to the Render dashboard → **Shell** → upload `model.pkl` and `vectorizer.pkl` directly, OR retrain using the shell:
> ```bash
> # Download dataset and retrain directly on Render shell
> python shield360_engine.py
> ```

---

### Step 3 — Deploy Dashboard on Vercel

1. Go to [vercel.com](https://vercel.com) and sign up (free)
2. Click **New Project** → import your GitHub repo
3. Set the **Root Directory** to `dashboard`
4. Add **Environment Variable**:
   - Key: `VITE_API_URL`
   - Value: `https://shield360-api.onrender.com`
5. Click **Deploy**
6. Your dashboard will be live at: `https://shield360.vercel.app`

---

### Step 4 — Update Chrome Extension for Production

In `chrome_extension/background.js`, change:
```javascript
const SHIELD360_SERVER = "http://127.0.0.1:5000";
```
to:
```javascript
const SHIELD360_SERVER = "https://shield360-api.onrender.com";
```

Then reload the extension in `chrome://extensions/`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check |
| POST | `/scan` | Scan a URL for threats |
| GET | `/logs` | Fetch scan history |
| GET | `/stats` | Dashboard summary stats |
| GET | `/allowlist` | List company-allowed domains |
| POST | `/allowlist` | Add domain to allowlist |
| DELETE | `/allowlist/<id>` | Remove domain from allowlist |
| DELETE | `/logs/clear` | Clear all scan logs |

---

## Threat Categories

| Status | Meaning |
|--------|---------|
| `benign` | Safe, no threat detected |
| `phishing` | Fake login / credential theft site |
| `malware` | Delivers viruses or ransomware |
| `defacement` | Hacked/vandalized website |
| `company_allowed` | Manually approved by admin |
