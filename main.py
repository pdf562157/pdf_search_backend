from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import json

app = FastAPI()

# Allow all origins for development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OCR_JSON_DIR = "ocr_json"
PDF_LINKS_FILE = "pdf_links.json"

# Load PDF-to-GDrive link mapping at startup
try:
    with open(PDF_LINKS_FILE, "r", encoding="utf-8") as f:
        pdf_links = json.load(f)
except FileNotFoundError:
    pdf_links = {}
    print("[WARNING] pdf_links.json not found.")
except json.JSONDecodeError as e:
    raise RuntimeError(f"[ERROR] Failed to load pdf_links.json: {e}")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/search")
def search_keyword(q: str = Query(..., description="Search keyword")):
    q_lower = q.lower()
    results = []

    for filename in os.listdir(OCR_JSON_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(OCR_JSON_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load {filename}: {e}")
            continue

        for page, text in ocr_data.items():
            if q_lower in text.lower():
                matched_para = next((p for p in text.split("\n\n") if q_lower in p.lower()), "")
                file_base = os.path.splitext(filename)[0]
                results.append({
                    "filename": file_base + ".pdf",
                    "page": page,
                    "paragraph": matched_para.strip(),
                    "link": pdf_links.get(file_base + ".pdf", "")
                })
                break  # Return only first match per file for performance

    return {"count": len(results), "results": results}
