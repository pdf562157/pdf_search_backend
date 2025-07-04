from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
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
except json.JSONDecodeError as e:
    raise RuntimeError(f"[ERROR] Failed to load pdf_links.json: {e}")

class SearchRequest(BaseModel):
    keywords: List[str]

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/search")
def search_keywords(req: SearchRequest):
    results = []

    for filename in os.listdir(OCR_JSON_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(OCR_JSON_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except Exception as e:
            continue

        for page, text in ocr_data.items():
            text_lower = text.lower()
            if all(k.lower() in text_lower for k in req.keywords):
                matched_para = next(
                    (p for p in text.split("\n\n") if all(k.lower() in p.lower() for k in req.keywords)),
                    ""
                )
                file_base = os.path.splitext(filename)[0]
                results.append({
                    "filename": file_base + ".pdf",
                    "page": page,
                    "paragraph": matched_para.strip(),
                    "link": pdf_links.get(file_base + ".pdf", "")
                })
                break  # One match per file

    return {"count": len(results), "results": results}
