import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from tokenizer import make_tokens

# --- CONFIGURATION ---
DATASET_FILE = 'malicious_phish.csv' 
MODEL_FILE = 'model.pkl'           
VECTORIZER_FILE = 'vectorizer.pkl'

# make_tokens is imported from tokenizer.py (shared with app.py)

# Known benign URLs to augment training (fixes false positives on common sites)
TRUSTED_BENIGN_URLS = [
    "https://google.com", "https://www.google.com", "https://google.com/search",
    "https://github.com", "https://www.github.com", "https://github.com/user/repo",
    "https://amazon.com", "https://www.amazon.com", "https://amazon.com/dp/123",
    "https://youtube.com", "https://www.youtube.com", "https://youtube.com/watch",
    "https://facebook.com", "https://www.facebook.com", "https://m.facebook.com",
    "https://microsoft.com", "https://www.microsoft.com", "https://docs.microsoft.com",
    "https://stackoverflow.com", "https://stackoverflow.com/questions/123",
    "https://reddit.com", "https://www.reddit.com", "https://old.reddit.com",
    "https://wikipedia.org", "https://en.wikipedia.org", "https://en.wikipedia.org/wiki/X",
    "https://linkedin.com", "https://www.linkedin.com", "https://twitter.com", "https://x.com",
    "https://netflix.com", "https://www.netflix.com", "https://apple.com", "https://www.apple.com",
    "https://cloudflare.com", "https://dropbox.com", "https://paypal.com", "https://stripe.com",
    "https://zoom.us", "https://slack.com", "https://medium.com", "https://discord.com",
]

# --- 2. TRAIN THE MODEL ---
def train_model():
    print("\n[STEP 1] Loading Raw Data...")
    try:
        try:
            urls_data = pd.read_csv(DATASET_FILE, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            urls_data = pd.read_csv(DATASET_FILE, encoding="latin-1", low_memory=False)
            print("   > Read with latin-1 encoding (file was not UTF-8).")
        # Normalize column names (some datasets use URL/Type)
        urls_data.columns = urls_data.columns.str.strip().str.lower()
        # Allow common alternate column names
        if "url" not in urls_data.columns:
            for alt in ("link", "website", "address"):
                if alt in urls_data.columns:
                    urls_data = urls_data.rename(columns={alt: "url"})
                    break
        if "type" not in urls_data.columns:
            for alt in ("label", "target", "category"):
                if alt in urls_data.columns:
                    urls_data = urls_data.rename(columns={alt: "type"})
                    break
        if "url" not in urls_data.columns or "type" not in urls_data.columns:
            print(f"[ERROR] CSV must have 'url' and 'type' columns. Found: {list(urls_data.columns)}")
            return
        urls_data = urls_data[["url", "type"]].copy()
        print(f"   > Loaded {len(urls_data)} rows.")
    except FileNotFoundError:
        print(f"[ERROR] '{DATASET_FILE}' not found.")
        print("   Get a URL dataset (columns: url, type) from Kaggle and save it as malicious_phish.csv in the project root.")
        print("   See README.md → 'Get the training dataset' for links.")
        return

    # --- DATA CLEANING STAGE (New) ---
    print("\n[STEP 2] Cleaning Data...")
    
    # 1. Drop Duplicates
    initial_count = len(urls_data)
    urls_data = urls_data.drop_duplicates()
    print(f"   > Removed {initial_count - len(urls_data)} duplicate rows.")

    # 2. Remove rows missing url or type only (other columns ignored)
    urls_data = urls_data.dropna(subset=["url", "type"])
    print(f"   > Dropped rows with missing url/type. Current count: {len(urls_data)}")

    # 3. Augment with trusted benign URLs (fixes "everything = phishing" on real sites)
    # Oversample trusted URLs (50x each) so model learns these patterns
    TRUSTED_REPEAT = 50
    aug_urls = TRUSTED_BENIGN_URLS * TRUSTED_REPEAT
    aug = pd.DataFrame({"url": aug_urls, "type": "benign"})
    urls_data = pd.concat([urls_data, aug], ignore_index=True)
    print(f"   > Augmented with {len(TRUSTED_BENIGN_URLS)} x {TRUSTED_REPEAT} = {len(aug_urls)} trusted benign URLs.")

    # 4. Use full dataset (no sampling)
    print(f"\n[STEP 3] Using Full Dataset...")
    print(f"   > Total rows: {len(urls_data)}")

    # --- PRE-PROCESSING STAGE ---
    y = urls_data["type"]
    url_list = urls_data["url"]

    print("\n[STEP 4] Pre-processing & Vectorization...")
    # TfidfVectorizer converts text to numbers (Feature Extraction)
    vectorizer = TfidfVectorizer(tokenizer=make_tokens, token_pattern=None)
    X = vectorizer.fit_transform(url_list)
    print("   > URLs converted to numerical vectors.")

    # Split Data (stratify only if every class has at least 2 samples)
    print("\n[STEP 5] Splitting Data (80% Train, 20% Test)...")
    min_class_count = y.value_counts().min()
    if min_class_count >= 2:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        print("   > One or more classes have <2 samples; split without stratification.")

    # --- TRAINING STAGE ---
    # Multinomial logistic regression: multiple URL classes (benign, phishing, malware, defacement)
    print("\n[STEP 6] Training Multinomial Logistic Regression Model...")
    logit = LogisticRegression(max_iter=1000)
    logit.fit(X_train, y_train)
    
    accuracy = logit.score(X_test, y_test)
    print(f"   > [SUCCESS] Model Accuracy on Test Data: {accuracy * 100:.2f}%")

    # --- SAVING ---
    print("\n[STEP 7] Saving System...")
    with open(VECTORIZER_FILE, "wb") as f:
        pickle.dump(vectorizer, f)
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(logit, f)

    print(f"   > Files '{VECTORIZER_FILE}' and '{MODEL_FILE}' saved successfully!")

# --- MAIN MENU ---
if __name__ == "__main__":
    while True:
        print("\n========================================")
        print("   SHIELD360 ENGINE (Supervisor Mode)")
        print("========================================")
        print("1. Run Data Cleaning & Train Model")
        print("2. Exit")
        choice = input("Select Option: ")

        if choice == '1':
            train_model()
        elif choice == '2':
            break