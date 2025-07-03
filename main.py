from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
import hashlib

app = FastAPI()

# Allow frontend connections (desktop GUI, mobile app, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------- Configuration --------
OCR_JSON_FOLDER = "ocr_json"  # Folder containing precomputed OCR JSONs
USERS_FILE = "users.json"     # To store approved users
GOOGLE_DRIVE_BASE = "https://drive.google.com/file/d/{file_id}/view?usp=sharing"

# Example: Mapping from filename to Google Drive file ID
DRIVE_MAPPING_FILE = "drive_links.json"

# -------- Data Models --------
class User(BaseModel):
    username: str
    password: str

class SignupRequest(User):
    email: str

class SearchRequest(BaseModel):
    keyword: str

# -------- Helpers --------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_drive_links():
    if not os.path.exists(DRIVE_MAPPING_FILE):
        return {}
    with open(DRIVE_MAPPING_FILE, "r") as f:
        return json.load(f)

def get_snippet(text: str, keyword: str, length: int = 100):
    keyword = keyword.lower()
    index = text.lower().find(keyword)
    if index == -1:
        return ""
    start = max(index - length // 2, 0)
    end = min(index + length // 2, len(text))
    return text[start:end].replace("\n", " ")

# -------- API Routes --------

@app.post("/signup")
def signup(user: SignupRequest):
    users = load_users()
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    users[user.username] = {
        "password": hash_password(user.password),
        "email": user.email,
        "approved": False
    }
    save_users(users)
    return {"message": "Signup request submitted. Wait for admin approval."}

@app.post("/login")
def login(user: User):
    users = load_users()
    if user.username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    if users[user.username]["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    if not users[user.username]["approved"]:
        raise HTTPException(status_code=403, detail="User not yet approved by admin")
    return {"message": "Login successful"}

@app.post("/search")
def search(req: SearchRequest):
    keyword = req.keyword.strip().lower()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")

    matches = []
    drive_links = load_drive_links()

    for filename in os.listdir(OCR_JSON_FOLDER):
        if filename.endswith(".json"):
            filepath = os.path.join(OCR_JSON_FOLDER, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for page, content in data.items():
                        if keyword in content.lower():
                            snippet = get_snippet(content, keyword)
                            pdf_name = filename.replace(".json", ".pdf")
                            file_id = drive_links.get(pdf_name, "UNKNOWN_ID")
                            matches.append({
                                "file": pdf_name,
                                "page": page,
                                "snippet": snippet,
                                "url": GOOGLE_DRIVE_BASE.format(file_id=file_id)
                            })
            except Exception as e:
                print(f"[ERROR] Failed to process {filename}: {e}")
                continue

    return {"matches": matches}
