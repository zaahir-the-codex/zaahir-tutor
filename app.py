import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import traceback

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

app = FastAPI(title="Zaahir's Grade 12 AI Tutor")

# Mount static files FIRST
app.mount("/static", StaticFiles(directory="static"), name="static")

# Then set up templates
templates = Jinja2Templates(directory="templates")

# Subjects list
SUBJECTS = [
    "Mathematics", "Mathematical Literacy", "Physical Sciences", "Life Sciences",
    "Business Studies", "Dramatic Arts", "Accounting", "Economics", "Geography",
    "History", "English Home Language", "Afrikaans", "Agricultural Sciences",
    "Tourism", "Consumer Studies", "Information Technology",
    "Computer Applications Technology", "Engineering Graphics and Design"
]

# ============================================================
# DATA MODELS
# ============================================================
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

# ============================================================
# AI FUNCTIONS
# ============================================================
def ask_groq(system_prompt: str, history: list, user_message: str) -> str:
    """Send message to Groq API."""
    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq API error: {e}")
        return f"Sorry, I'm having trouble. Error: {str(e)}"

def generate_dbe_paper(subject: str, paper_number: int, total_marks: int, 
                       duration: float, topics: list, include_memo: bool) -> dict:
    """Generate an authentic DBE-style exam paper."""
    
    topics_text = ", ".join(topics) if topics else "all CAPS curriculum topics"
    current_year = datetime.now().year
    
    system_prompt = """You are an expert South African NSC exam paper setter with 20 years of experience.
You follow the CAPS curriculum precisely. Create authentic, fair papers."""
    
    user_message = f"""Create a Grade 12 {subject} Paper {paper_number} examination in official DBE/NSC format.

SPECIFICATIONS:
- Total marks: {total_marks}
- Duration: {duration} hours
- Topics: {topics_text}
- Year: {current_year}

FORMAT REQUIREMENTS:
1. Start with "NATIONAL SENIOR CERTIFICATE"
2. Next line: "GRADE 12"
3. Next line: "{subject.upper()} P{paper_number}"
4. Next line: "NOVEMBER {current_year}"
5. Then: "MARKS: {total_marks}" and "TIME: {duration} hours"
6. Add "This question paper consists of X pages."
7. Add "INSTRUCTIONS AND INFORMATION" with 8-10 standard instructions
8. Divide into SECTIONS (A, B, C) with increasing difficulty
9. Every question must show mark allocation in brackets: e.g., (3)
10. End with "TOTAL: {total_marks} MARKS"

Create an authentic exam paper with proper spacing and professional formatting."""

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
        memo_prompt = f"""Create a marking memorandum for the Grade 12 {subject} Paper {paper_number} exam.

REQUIREMENTS:
1. Start with "MARKING MEMORANDUM - {subject} P{paper_number}"
2. Follow the same question numbering
3. For each question, provide:
   - Model answer
   - Mark allocation per step
   - Accepted alternative answers
4. Show calculation steps clearly

Format like a real DBE marking guideline."""
        
        result["memo"] = ask_groq(system_prompt, [], memo_prompt)
    
    return result

# ============================================================
# API ENDPOINTS
# ============================================================
@app.get("/")
async def home(request: Request):
    """Serve the main page."""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        print(f"Template error: {e}")
        traceback.print_exc()
        return HTMLResponse(f"<h1>Error loading page</h1><p>{str(e)}</p>", status_code=500)

@app.get("/subjects")
async def get_subjects():
    return {"subjects": SUBJECTS}

@app.get("/stats")
async def get_stats():
    return {"total_chunks": 0, "status": "ready"}

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
You follow the CAPS curriculum strictly. You are warm, patient, and encouraging.
Solve problems step by step, showing all working.

Answer thoroughly and clearly. End by asking if they need further clarification."""

        answer = ask_groq(system_prompt, req.history, req.message)
        return {
            "answer": answer,
            "sources": [],
            "model_used": f"Groq ({GROQ_MODEL})"
        }
    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-paper")
async def generate_paper(req: PaperRequest):
    try:
        result = generate_dbe_paper(
            subject=req.subject,
            paper_number=req.paper_number,
            total_marks=req.total_marks,
            duration=req.duration_hours,
            topics=req.topics,
            include_memo=req.include_memo
        )
        return result
    except Exception as e:
        print(f"Paper generation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-about-selection")
async def ask_about_selection(req: AskAboutSelection):
    try:
        system_prompt = f"""You are an expert South African Grade 12 tutor specialising in {req.subject}.
The student has highlighted a specific part. Focus ONLY on explaining the selected text thoroughly.
Break it down step by step with examples."""

        user_message = f"""The student highlighted this text:
---
{req.selected_text}
---
Please explain this in detail. Break it down, show examples, and help the student understand completely."""

        answer = ask_groq(system_prompt, req.history, user_message)
        return {
            "answer": answer,
            "selected_text": req.selected_text,
            "model_used": f"Groq ({GROQ_MODEL})"
        }
    except Exception as e:
        print(f"Ask about selection error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
