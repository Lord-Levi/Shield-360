"""
Render startup script — downloads model files from GitHub Releases if missing.
Set the environment variable MODEL_DOWNLOAD_URL in Render dashboard.
"""
import os
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "model.pkl"
VECTORIZER_FILE = BASE_DIR / "vectorizer.pkl"

def download_file(url: str, dest: Path):
    print(f"[STARTUP] Downloading {dest.name} from {url} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"[STARTUP] {dest.name} saved ({dest.stat().st_size // 1024} KB)")

model_url      = os.environ.get("MODEL_URL")
vectorizer_url = os.environ.get("VECTORIZER_URL")

if not MODEL_FILE.exists():
    if model_url:
        download_file(model_url, MODEL_FILE)
    else:
        print("[STARTUP] WARNING: model.pkl not found and MODEL_URL not set.")

if not VECTORIZER_FILE.exists():
    if vectorizer_url:
        download_file(vectorizer_url, VECTORIZER_FILE)
    else:
        print("[STARTUP] WARNING: vectorizer.pkl not found and VECTORIZER_URL not set.")
