import os
import requests
import time
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

load_dotenv()

# ============================================================
# GROQ API CONFIGURATION
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

print("=" * 50)
print("🎓 Zaahir's Tutor Starting...")
print(f"✅ GROQ_API_KEY present: {'YES' if GROQ_API_KEY else 'NO'}")
print(f"🤖 Using model: {GROQ_MODEL}")
print("=" * 50)

# Settings
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./vectordb")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

# Create folders
Path(DOCUMENTS_PATH).mkdir(parents=True, exist_ok=True)
Path("./static").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Zaahir's Grade 12 AI Tutor")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Subjects
SUBJECTS = [
    "Mathematics", "Mathematical Literacy", "Physical Sciences", "Life Sciences",
    "Business Studies", "Dramatic Arts", "Accounting", "Economics", "Geography",
    "History", "English Home Language", "Afrikaans", "Agricultural Sciences",
    "Tourism", "Consumer Studies", "Information Technology",
    "Computer Applications Technology", "Engineering Graphics and Design"
]

fetch_progress = {"status": "idle", "message": "", "completed": [], "failed": [], "total": 0}

class ChatRequest(BaseModel):
    message: str
    subject: str = "Mathematics"
    history: list = []

class PaperRequest(BaseModel):
    subject: str
    total_marks: int = 150
    duration_hours: float = 3.0
    paper_number: int = 1
    topics: list = []
    include_memo: bool = True

class AskAboutSelection(BaseModel):
    selected_text: str
    subject: str = "Mathematics"
    history: list = []

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
        return f"Sorry, I'm having trouble. Error: {str(e)}"

def generate_dbe_style_paper(subject: str, paper_number: int, total_marks: int, duration: float, topics: list, include_memo: bool) -> dict:
    topics_text = ", ".join(topics) if topics else "all CAPS curriculum topics"
    
    system_prompt = """You are an expert South African NSC exam paper setter with 20 years of experience setting papers for the Department of Basic Education. You follow the CAPS curriculum precisely. Create papers that are authentic, fair, and assess learners at appropriate cognitive levels."""
    
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
5. Then: "MARKS: {total_marks}" and "TIME: {duration} hours"
6. Include "INSTRUCTIONS AND INFORMATION" section with standard DBE instructions
7. Divide into SECTIONS (A, B, C) with increasing difficulty
8. Every question must have mark allocation in brackets: e.g., (3)
9. End with "TOTAL: {total_marks} MARKS"

Format exactly like a real DBE exam paper."""

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
        memo_prompt = f"""Based on the Grade 12 {subject} Paper {paper_number} you just created, create the OFFICIAL MARKING MEMORANDUM.

REQUIREMENTS:
1. Start with "MARKING MEMORANDUM - {subject} P{paper_number}"
2. Follow the same question numbering
3. For each question, provide model answer and mark allocation
4. Show calculation steps clearly

Format like a real DBE marking guideline."""
        
        result["memo"] = ask_groq(system_prompt, [], memo_prompt)
    
    return result

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/subjects")
async def get_subjects():
    return {"subjects": SUBJECTS}

@app.get("/fetch-status")
async def get_fetch_status():
    return fetch_progress

@app.post("/fetch-papers")
async def fetch_papers(req: dict, background_tasks: BackgroundTasks):
    return {"status": "started", "message": "Fetch feature coming soon"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), subject: str = Form("Mathematics")):
    return JSONResponse({
        "success": False,
        "message": "Image upload is currently disabled. Please type your question directly.",
        "filename": file.filename
    })

@app.post("/chat")
async def chat(req: ChatRequest):
    system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
You follow the CAPS curriculum strictly. You are warm, patient, and encouraging.
When a student selects text and asks about it, you explain that specific part thoroughly.
Solve problems step by step, showing all working.

INSTRUCTIONS:
- Answer thoroughly and clearly
- Show all calculations step by step
- Always encourage the learner
- End by asking if they need further clarification"""

    try:
        answer = ask_groq(system_prompt, req.history, req.message)
        return {"answer": answer, "sources": [], "model_used": f"Groq ({GROQ_MODEL})"}
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
    system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
The student has highlighted a specific part of an exam paper or explanation.
Focus ONLY on explaining the selected text thoroughly.
Break it down step by step."""

    user_message = f"""The student highlighted this text:
---
{req.selected_text}
---
Please explain this in detail. Break it down, show examples, and help the student understand."""

    try:
        answer = ask_groq(system_prompt, req.history, user_message)
        return {"answer": answer, "selected_text": req.selected_text, "model_used": f"Groq ({GROQ_MODEL})"}
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
