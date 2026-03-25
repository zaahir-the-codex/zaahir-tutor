import os
import requests
import subprocess
import time
import shutil
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
from PIL import Image
import pytesseract
import io

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./vectordb")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

# Create uploads folder
UPLOADS_PATH = Path(DOCUMENTS_PATH) / "uploads"
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Grade 12 AI Tutor")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

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
YEARS = [2024, 2023, 2022, 2021, 2020, 2019, 2018]

fetch_progress = {
    "status": "idle",
    "message": "",
    "current_file": "",
    "completed": [],
    "failed": [],
    "total": 0,
    "fetched_subject": None,
    "fetched_paper": None,
    "fetched_year": None
}

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

class FetchRequest(BaseModel):
    subject: str
    year: int
    paper_number: int
    include_memo: bool = True

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from an image using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if needed
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from various file types."""
    ext = filename.lower().split('.')[-1]
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return extract_text_from_image(file_bytes)
    elif ext == 'pdf':
        # For PDFs, we'll just return a note that PDF upload is supported
        # but for full OCR we'd need pdf2image which is heavy
        return "[PDF uploaded. For best results, upload images of specific questions.]"
    elif ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')
    else:
        return f"[File uploaded: {filename}. Content extraction not fully supported yet.]"

def get_embedding(text: str) -> list:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text[:2000]}  # Limit text length
    )
    response.raise_for_status()
    return response.json()["embedding"]

def search_documents(query: str, n_results: int = 5) -> list:
    try:
        collection = chroma_client.get_collection("grade12_documents")
    except Exception:
        return []
    try:
        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            source = results["metadatas"][0][i].get("source", "Unknown")
            chunks.append(f"[From: {source}]\n{doc}")
        return chunks
    except Exception:
        return []

def ask_ollama(system_prompt: str, history: list, user_message: str) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=300
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

def run_ingestion():
    try:
        result = subprocess.run(
            ["python", "ingest.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Ingestion failed: {e}")
        return False

async def fetch_papers_task(subject: str, year: int, paper_number: int, include_memo: bool):
    global fetch_progress
    
    subject_url_name = SUBJECTS.get(subject, subject.replace(" ", "%20"))
    year_folder = f"{year}%20November%20past%20papers"
    base_url = f"https://www.education.gov.za/Portals/0/CD/{year_folder}"
    
    files_to_fetch = []
    
    paper_urls = [
        f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20Eng.pdf",
        f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20Eng.pdf?ver=2025-03-04-110202-327",
        f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20English.pdf",
    ]
    
    paper_dest = Path(DOCUMENTS_PATH) / "past_papers" / f"{subject} P{paper_number} Nov {year} Eng.pdf"
    files_to_fetch.append((paper_urls, paper_dest, "question"))
    
    if include_memo:
        memo_urls = [
            f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20MG%20Afr%20%26%20Eng.pdf",
            f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20Memo%20Eng.pdf",
            f"{base_url}/{subject_url_name}%20P{paper_number}%20Nov%20{year}%20MG.pdf",
        ]
        memo_dest = Path(DOCUMENTS_PATH) / "memos" / f"{subject} P{paper_number} Nov {year} MG.pdf"
        files_to_fetch.append((memo_urls, memo_dest, "memo"))
    
    fetch_progress["total"] = len(files_to_fetch)
    fetch_progress["status"] = "downloading"
    fetch_progress["completed"] = []
    fetch_progress["failed"] = []
    
    for urls, dest, file_type in files_to_fetch:
        fetch_progress["current_file"] = f"{subject} P{paper_number} ({file_type})"
        fetch_progress["message"] = f"Downloading {dest.name}..."
        
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        downloaded = False
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=60)
                if response.status_code == 200:
                    with open(dest, 'wb') as f:
                        f.write(response.content)
                    downloaded = True
                    fetch_progress["completed"].append(str(dest.name))
                    fetch_progress["message"] = f"Downloaded: {dest.name}"
                    break
            except:
                continue
            time.sleep(0.5)
        
        if not downloaded:
            fetch_progress["failed"].append(str(dest.name))
            fetch_progress["message"] = f"Failed: {dest.name}"
        
        time.sleep(0.5)
    
    if fetch_progress["completed"]:
        fetch_progress["status"] = "ingesting"
        fetch_progress["message"] = "Loading documents into database..."
        
        if run_ingestion():
            fetch_progress["status"] = "complete"
            fetch_progress["message"] = f"Success! Added {len(fetch_progress['completed'])} files."
            fetch_progress["fetched_subject"] = subject
            fetch_progress["fetched_paper"] = paper_number
            fetch_progress["fetched_year"] = year
        else:
            fetch_progress["status"] = "error"
            fetch_progress["message"] = "Ingestion failed."
    else:
        fetch_progress["status"] = "error"
        fetch_progress["message"] = "No files were downloaded."
    
    fetch_progress["current_file"] = ""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/subjects")
async def get_subjects():
    return {"subjects": SUBJECT_LIST}

@app.get("/years")
async def get_years():
    return {"years": YEARS}

@app.get("/fetch-status")
async def get_fetch_status():
    return fetch_progress

@app.post("/fetch-papers")
async def fetch_papers(req: FetchRequest, background_tasks: BackgroundTasks):
    if fetch_progress["status"] not in ["idle", "complete", "error"]:
        raise HTTPException(status_code=409, detail="A fetch operation is already in progress")
    
    background_tasks.add_task(fetch_papers_task, req.subject, req.year, req.paper_number, req.include_memo)
    return {"status": "started", "message": f"Fetching {req.subject} Paper {req.paper_number} for {req.year}"}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    subject: str = Form("Mathematics")
):
    """Upload a file (image, PDF, document) and extract text from it."""
    try:
        # Read file contents
        contents = await file.read()
        filename = file.filename
        
        # Generate unique ID for this upload
        file_id = uuid.uuid4().hex[:8]
        saved_filename = f"{file_id}_{filename}"
        file_path = UPLOADS_PATH / saved_filename
        
        # Save original file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Extract text from file
        extracted_text = extract_text_from_file(contents, filename)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            return JSONResponse({
                "success": False,
                "message": "Could not extract readable text from this file. Try uploading a clearer image of the problem.",
                "filename": filename
            })
        
        # Store extracted text as a document in vector DB
        try:
            collection = chroma_client.get_or_create_collection("grade12_documents")
            
            # Create embedding and store
            embedding = get_embedding(extracted_text[:2000])
            doc_id = f"upload_{file_id}"
            
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[extracted_text],
                metadatas=[{
                    "source": f"Uploaded: {filename}",
                    "category": "uploads",
                    "subject": subject,
                    "timestamp": datetime.now().isoformat()
                }]
            )
            
            return JSONResponse({
                "success": True,
                "message": f"Successfully uploaded and processed '{filename}'",
                "filename": filename,
                "extracted_text_preview": extracted_text[:500],
                "characters": len(extracted_text)
            })
            
        except Exception as e:
            return JSONResponse({
                "success": False,
                "message": f"File saved but failed to index: {str(e)}",
                "filename": filename
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/chat")
async def chat(req: ChatRequest):
    relevant_chunks = search_documents(query=req.message, n_results=5)

    if relevant_chunks:
        context = "\n\n---\n\n".join(relevant_chunks)
        context_note = "Use the uploaded documents and past paper content below to inform your answer."
    else:
        context = "No documents loaded yet. Answer from general knowledge."
        context_note = "No documents loaded yet — answering from general knowledge."

    system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
You follow the CAPS curriculum strictly.
You are warm, patient, encouraging and clear. You explain concepts step by step.
When a student uploads an image of a problem, you can see the extracted text in the context.
Solve problems step by step, showing all working.
You use examples relevant to South African students.
You remember the full conversation.

{context_note}

RELEVANT CONTENT FROM DOCUMENTS AND PAST PAPERS:
{context}

INSTRUCTIONS:
- Answer thoroughly and clearly
- If the user uploaded a problem, solve it step by step
- Show all calculations
- Reference relevant documents
- Always encourage the learner
- End by asking if they need further clarification"""

    try:
        answer = ask_ollama(system_prompt, req.history, req.message)
        sources = []
        for chunk in relevant_chunks:
            first_line = chunk.split("\n")[0]
            if first_line not in sources:
                sources.append(first_line)
        return {
            "answer": answer,
            "sources": sources,
            "model_used": OLLAMA_MODEL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-paper")
async def generate_paper(req: PaperRequest):
    relevant_chunks = search_documents(
        query=f"Grade 12 {req.subject} exam questions",
        n_results=6
    )

    if relevant_chunks:
        context = "\n\n---\n\n".join(relevant_chunks)
        context_note = "Use the past paper style below as a reference for formatting and difficulty."
    else:
        context = "No past papers loaded yet."
        context_note = "No past papers loaded — generating in standard NSC format from knowledge."

    topics_text = ", ".join(req.topics) if req.topics else "all CAPS topics for this subject"

    system_prompt = """You are an expert South African NSC exam paper setter with years of experience
setting papers for the Department of Basic Education.
You follow CAPS curriculum requirements precisely.
You create fair, well-structured papers that test learners at all cognitive levels."""

    user_message = f"""Create a complete Grade 12 {req.subject} Paper {req.paper_number} exam.

SPECIFICATIONS:
- Total marks: {req.total_marks}
- Duration: {req.duration_hours} hours
- Topics: {topics_text}
- Year: {datetime.now().year}

{context_note}

PAST PAPER REFERENCE:
{context}

REQUIREMENTS FOR THE QUESTION PAPER:
1. Proper NSC header with subject, grade, paper number, duration and total marks
2. Clear instructions to learners
3. Divide into Section A, Section B and Section C
4. Every question must show mark allocation in brackets e.g. (3)
5. End with TOTAL: {req.total_marks} MARKS

Then on a new line write exactly: ---MEMORANDUM---

Then write a complete memorandum with model answers and marks."""

    try:
        paper = ask_ollama(system_prompt, [], user_message)
        return {
            "paper": paper,
            "subject": req.subject,
            "generated_at": datetime.now().isoformat(),
            "model_used": OLLAMA_MODEL
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
