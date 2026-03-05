import tkinter as tk
from tkinter import messagebox, simpledialog
import pickle

# --- CONFIGURATION ---
MODEL_FILE = 'model.pkl'
VECTORIZER_FILE = 'vectorizer.pkl'

# --- 1. THE MISSING PIECE (Custom Tokenizer) ---
# The model needs this function to exist to load correctly
def make_tokens(f):
    tokens_by_slash = str(f).split('/')
    total_tokens = []
    for i in tokens_by_slash:
        tokens = str(i).split('-')
        tokens_dot = []
        for j in tokens:
            temp_tokens = str(j).split('.')
            tokens_dot = tokens_dot + temp_tokens
        total_tokens = total_tokens + tokens + tokens_dot
    total_tokens = list(set(total_tokens))
    for noise in ('com', 'www', 'https:', 'http:', ''):
        if noise in total_tokens:
            total_tokens.remove(noise)
    return total_tokens

# --- 2. LOAD THE BRAIN ---
model = None
vectorizer = None

def load_model():
    global model, vectorizer
    try:
        with open(VECTORIZER_FILE, "rb") as f:
            vectorizer = pickle.load(f)
        with open(MODEL_FILE, "rb") as f:
            model = pickle.load(f)
        print("[INFO] Model loaded successfully.")
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

# --- 3. SCAN FUNCTION ---
def scan_url():
    # Check if model is loaded
    if not model:
        if not load_model():
            messagebox.showerror("Error", "Model files missing or corrupt!\n\nPlease run 'shield360_engine.py' and select Option 1.")
            return

    # Get URL from Popup
    url = simpledialog.askstring("Input", "Paste the URL here:")
    
    if url:
        try:
            # Predict
            url_vector = vectorizer.transform([url])
            prediction = model.predict(url_vector)[0]
            
            # Show Result
            if prediction == 'benign': # Benign means Safe
                messagebox.showinfo("Result", "✅ SAFE: This URL looks clean.")
            else:
                messagebox.showwarning("Result", f"⛔ DANGER: Detected as {prediction.upper()}")

        except Exception as e:
            messagebox.showerror("Error", f"Prediction Failed: {e}")

# --- 4. BUILD THE WINDOW ---
root = tk.Tk()
root.title("Shield360 - Final Prototype")
root.geometry("400x300")

# Header
label_title = tk.Label(root, text="Shield360 Detector", font=("Arial", 16, "bold"))
label_title.pack(pady=30)

# --- THE BIG BLUE BUTTON ---
btn = tk.Button(root, text="SCAN NEW URL", font=("Arial", 14, "bold"), bg="#007acc", fg="white", padx=20, pady=10, command=scan_url)
btn.pack(pady=10)

# Footer
label_footer = tk.Label(root, text="Protected by AI", font=("Arial", 10), fg="gray")
label_footer.pack(side=tk.BOTTOM, pady=10)

# Load model on start
load_model()

root.mainloop()