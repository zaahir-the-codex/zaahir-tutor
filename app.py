import os
import requests
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv
import chromadb
import uuid
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import io
import json

load_dotenv()

# ============================================================
# GROQ API CONFIGURATION
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Print startup info
print("=" * 50)
print("🎓 Zaahir's Tutor Starting...")
print(f"✅ GROQ_API_KEY present: {'YES' if GROQ_API_KEY else 'NO'}")
print(f"🤖 Using model: {GROQ_MODEL}")
print("=" * 50)

# Settings
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./vectordb")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

# Create folders
UPLOADS_PATH = Path(DOCUMENTS_PATH) / "uploads"
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Zaahir's Grade 12 AI Tutor")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Subjects
SUBJECTS = {
    "Mathematics": "Mathematics",
    "Mathematical Literacy": "Mathematical%20Literacy", 
    "Physical Sciences": "Physical%20Sciences",
    "Life Sciences": "Life%20Sciences",
    "Business Studies": "Business%20Studies",
    "Dramatic Arts": "Dramatic%20Arts",
    "Accounting": "Accounting",
    "Economics": "Economics",
    "Geography": "Geography",
    "History": "History",
    "English Home Language": "English%20Home%20Language",
    "Afrikaans": "Afrikaans",
    "Agricultural Sciences": "Agricultural%20Sciences",
    "Tourism": "Tourism",
    "Consumer Studies": "Consumer%20Studies",
    "Information Technology": "Information%20Technology",
    "Computer Applications Technology": "Computer%20Applications%20Technology",
    "Engineering Graphics and Design": "Engineering%20Graphics%20and%20Design",
}

SUBJECT_LIST = list(SUBJECTS.keys())

fetch_progress = {
    "status": "idle",
    "message": "",
    "current_file": "",
    "completed": [],
    "failed": [],
    "total": 0,
}

class ChatRequest(BaseModel):
    message: str
    subject: str = "Mathematics"
    history: list = []
    selected_text: str = ""  # For highlighted text

class PaperRequest(BaseModel):
    subject: str
    total_marks: int = 150
    duration_hours: float = 3.0
    paper_number: int = 1
    topics: list = []
    include_memo: bool = True

class FetchRequest(BaseModel):
    subject: str
    year: int
    paper_number: int
    include_memo: bool = True

class AskAboutSelection(BaseModel):
    selected_text: str
    subject: str = "Mathematics"
    context: str = ""
    history: list = []

# ============================================================
# OCR FUNCTIONS
# ============================================================
def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')
        if image.mode != 'L':
            image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        if image.width < 1200:
            ratio = 1200 / image.width
            new_size = (1200, int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        texts = []
        configs = [r'--oem 3 --psm 6 -l eng', r'--oem 3 --psm 11 -l eng', r'--oem 3 --psm 7 -l eng']
        for config in configs:
            text = pytesseract.image_to_string(image, config=config)
            if text.strip():
                texts.append(text.strip())
        if texts:
            return max(texts, key=len)
        return ""
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return extract_text_from_image(file_bytes)
    elif ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')
    return ""

def get_embedding(text: str) -> list:
    return [0.0] * 384

def search_documents(query: str, n_results: int = 5) -> list:
    try:
        collection = chroma_client.get_collection("grade12_documents")
        return []
    except Exception:
        return []

# ============================================================
# AI FUNCTIONS
# ============================================================
def ask_groq(system_prompt: str, history: list, user_message: str) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 4000}
    
    try:
        response = requests.post(f"{GROQ_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq API error: {e}")
        return f"Sorry, I'm having trouble. Error: {str(e)}"

# ============================================================
# PAPER GENERATION WITH DBE STYLE
# ============================================================
def generate_dbe_style_paper(subject: str, paper_number: int, total_marks: int, duration: float, topics: list, include_memo: bool) -> dict:
    """Generate a paper in authentic DBE/NSC format."""
    
    topics_text = ", ".join(topics) if topics else "all CAPS curriculum topics"
    
    system_prompt = """You are an expert South African NSC (National Senior Certificate) exam paper setter with 20 years of experience setting papers for the Department of Basic Education. You follow the CAPS curriculum precisely. Create papers that are authentic, fair, and assess learners at appropriate cognitive levels."""
    
    user_message = f"""Create a Grade 12 {subject} Paper {paper_number} examination paper in the official DBE/NSC format.

SPECIFICATIONS:
- Total marks: {total_marks}
- Duration: {duration} hours
- Topics to cover: {topics_text}
- Year: {datetime.now().year}

REQUIREMENTS - EXACT DBE FORMAT:
1. Start with "NATIONAL SENIOR CERTIFICATE" as the header
2. Next line: "GRADE 12"
3. Next line: "{subject.upper()} P{paper_number}"
4. Next line: "NOVEMBER {datetime.now().year}"
5. Then: "MARKS: {total_marks}" and "TIME: {duration} hours" on separate lines
6. Include "This question paper consists of X pages and an information sheet." (estimate pages)
7. Include "INSTRUCTIONS AND INFORMATION" section with 8-10 standard DBE instructions
8. Divide into SECTIONS (A, B, C) with increasing difficulty
9. Section A: Short questions, multiple choice, definitions (30-40% of marks)
10. Section B: Medium-length questions requiring calculations and explanations (30-40% of marks)
11. Section C: Longer, problem-solving questions (20-30% of marks)
12. Every question must have mark allocation in brackets: e.g., (3)
13. Include diagrams or data where appropriate
14. End with "TOTAL: {total_marks} MARKS"

Format the paper exactly like a real DBE exam paper. Use proper spacing, numbering, and professional language."""

    paper_content = ask_groq(system_prompt, [], user_message)
    
    result = {
        "paper": paper_content,
        "subject": subject,
        "paper_number": paper_number,
        "total_marks": total_marks,
        "duration": duration,
        "generated_at": datetime.now().isoformat(),
        "model_used": f"Groq ({GROQ_MODEL})"
    }
    
    if include_memo:
        memo_prompt = f"""Based on the Grade 12 {subject} Paper {paper_number} you just created, now create the OFFICIAL MARKING MEMORANDUM.

REQUIREMENTS:
1. Start with: "MARKING MEMORANDUM - {subject} P{paper_number}"
2. Follow the exact same question numbering
3. For each question, provide:
   - The model answer
   - Mark allocation per step/sub-question
   - Accepted alternative answers where applicable
   - Notes for markers (e.g., "accept any relevant example")
4. Show calculation steps clearly
5. Total marks should match the question paper

Format like a real DBE marking guideline."""
        
        memo_content = ask_groq(system_prompt, [], memo_prompt)
        result["memo"] = memo_content
    
    return result

# ============================================================
# API ENDPOINTS
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/subjects")
async def get_subjects():
    return {"subjects": SUBJECT_LIST}

@app.get("/fetch-status")
async def get_fetch_status():
    return fetch_progress

@app.post("/fetch-papers")
async def fetch_papers(req: FetchRequest, background_tasks: BackgroundTasks):
    if fetch_progress["status"] not in ["idle", "complete", "error"]:
        raise HTTPException(status_code=409, detail="A fetch operation is already in progress")
    return {"status": "started"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), subject: str = Form("Mathematics")):
    try:
        contents = await file.read()
        filename = file.filename
        extracted_text = extract_text_from_file(contents, filename)
        
        if extracted_text and len(extracted_text.strip()) > 10:
            return JSONResponse({
                "success": True,
                "message": f"Successfully uploaded '{filename}'",
                "filename": filename,
                "extracted_text": extracted_text,
                "extracted_text_preview": extracted_text[:500],
                "characters": len(extracted_text)
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Could not extract readable text. Try a clearer photo with good lighting.",
                "filename": filename
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/chat")
async def chat(req: ChatRequest):
    relevant_chunks = search_documents(query=req.message, n_results=5)
    context = "\n\n---\n\n".join(relevant_chunks) if relevant_chunks else "No documents loaded yet."

    system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
You follow the CAPS curriculum strictly. You are warm, patient, and encouraging.
When a student selects text and asks about it, you explain that specific part thoroughly.
Solve problems step by step, showing all working.

{context}

INSTRUCTIONS:
- Answer thoroughly and clearly
- Show all calculations step by step
- Always encourage the learner
- End by asking if they need further clarification"""

    try:
        answer = ask_groq(system_prompt, req.history, req.message)
        return {
            "answer": answer,
            "sources": [],
            "model_used": f"Groq ({GROQ_MODEL})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-paper")
async def generate_paper(req: PaperRequest):
    try:
        result = generate_dbe_style_paper(
            subject=req.subject,
            paper_number=req.paper_number,
            total_marks=req.total_marks,
            duration=req.duration_hours,
            topics=req.topics,
            include_memo=req.include_memo
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-about-selection")
async def ask_about_selection(req: AskAboutSelection):
    """Handle when user highlights text and asks about it."""
    system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
The student has highlighted a specific part of an exam paper or explanation and wants you to explain it.
Focus ONLY on explaining the selected text thoroughly.
Break it down step by step.
Use examples relevant to South African students."""

    user_message = f"""The student highlighted this text from an exam paper or explanation:

---
{req.selected_text}
---

Please explain this in detail. Break it down, show examples, and help the student understand it completely."""

    try:
        answer = ask_groq(system_prompt, req.history, user_message)
        return {
            "answer": answer,
            "selected_text": req.selected_text,
            "model_used": f"Groq ({GROQ_MODEL})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    try:
        collection = chroma_client.get_collection("grade12_documents")
        count = collection.count()
        return {"total_chunks": count, "status": "ready"}
    except Exception:
        return {"total_chunks": 0, "status": "no_documents_yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
