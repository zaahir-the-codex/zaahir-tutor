import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
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
# COMPLETE HTML WITH WORKING MENU
# ============================================================
HTML_CONTENT = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zaahir's Tutor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f1117; color: #e8e8f0; transition: background 0.2s; }
        
        /* Header */
        .header { background: #1a1d2e; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3148; }
        .header-left { display: flex; align-items: center; gap: 15px; }
        .menu-btn { background: #7c9eff; border: none; color: #0f1117; padding: 10px 18px; font-size: 18px; cursor: pointer; border-radius: 8px; font-weight: bold; }
        .menu-btn:hover { opacity: 0.85; }
        .header h1 { font-size: 20px; color: #7c9eff; }
        .header .sub { font-size: 11px; color: #666; margin-top: 2px; }
        .stats { background: #252840; padding: 5px 12px; border-radius: 20px; font-size: 12px; }
        
        /* Menu Panel */
        .overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 999; }
        .overlay.show { display: block; }
        .menu-panel { position: fixed; top: 0; left: -300px; width: 280px; height: 100%; background: #1a1d2e; z-index: 1000; transition: left 0.3s; padding: 20px; overflow-y: auto; border-right: 1px solid #2d3148; }
        .menu-panel.show { left: 0; }
        .menu-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #2d3148; }
        .menu-header h3 { color: #7c9eff; }
        .close-btn { background: none; border: none; color: #7c9eff; font-size: 24px; cursor: pointer; }
        .menu-section { margin-bottom: 20px; }
        .menu-section-label { font-size: 11px; text-transform: uppercase; color: #666; margin-bottom: 8px; letter-spacing: 0.5px; }
        .mode-btn, select, input { width: 100%; padding: 10px; margin-bottom: 8px; background: #1e2140; border: 1px solid #2d3148; border-radius: 8px; color: #e8e8f0; cursor: pointer; font-family: inherit; }
        .mode-btn.active { background: #1e2a5e; border-color: #7c9eff; color: #7c9eff; font-weight: bold; }
        .gen-btn { background: #7c9eff; color: #0f1117; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px; }
        .gen-btn:hover { opacity: 0.85; }
        .gen-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .hidden { display: none; }
        .theme-btn { padding: 8px; border-radius: 6px; cursor: pointer; background: #1e2140; border: 1px solid #2d3148; color: #e8e8f0; }
        
        /* Chat Area */
        .main { display: flex; flex-direction: column; height: calc(100vh - 70px); }
        .chat-area { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        .msg { max-width: 85%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; font-size: 14px; }
        .msg.user { align-self: flex-end; background: #1e2a5e; color: #c8d8ff; border-radius: 16px 16px 4px 16px; }
        .msg.ai { align-self: flex-start; background: #161925; border: 1px solid #2a2d45; border-radius: 4px 16px 16px 16px; width: 100%; }
        .msg.ai pre { background: #0f1117; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 8px 0; font-size: 12px; }
        .paper-container { background: #1a1d2e; border: 1px solid #2d3148; border-radius: 12px; padding: 16px; margin: 8px 0; font-family: monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
        .thinking { align-self: flex-start; color: #666; font-style: italic; padding: 10px; background: #161925; border-radius: 8px; }
        .input-bar { padding: 15px 20px; border-top: 1px solid #2d3148; background: #1a1d2e; display: flex; gap: 10px; align-items: flex-end; }
        .chat-input { flex: 1; padding: 12px; background: #1e2140; border: 1px solid #2d3148; border-radius: 12px; color: #e8e8f0; resize: none; font-family: inherit; font-size: 14px; }
        .chat-input:focus { outline: none; border-color: #7c9eff; }
        .send-btn { padding: 12px 24px; background: #7c9eff; border: none; border-radius: 12px; color: #0f1117; font-weight: bold; cursor: pointer; }
        .send-btn:hover { opacity: 0.85; }
        .welcome { background: #161925; padding: 20px; border-radius: 12px; line-height: 1.6; color: #9099bb; border: 1px solid #2a2d45; }
        .welcome strong { color: #7c9eff; }
        .model-tag { font-size: 10px; color: #666; margin-top: 8px; }
        .selection-toolbar { position: fixed; background: #7c9eff; color: #0f1117; padding: 8px 16px; border-radius: 30px; cursor: pointer; z-index: 1001; font-size: 12px; display: flex; gap: 8px; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        .selection-toolbar button { background: none; border: none; color: #0f1117; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <button class="menu-btn" id="menuButton">☰</button>
        <div>
            <h1>Zaahir's Tutor</h1>
            <div class="sub">Grade 12 · SA CAPS Curriculum</div>
        </div>
    </div>
    <div class="stats"><span id="docCount">0</span> chunks</div>
</div>

<div class="overlay" id="overlay"></div>
<div class="menu-panel" id="menuPanel">
    <div class="menu-header">
        <h3>Menu</h3>
        <button class="close-btn" id="closeMenuBtn">✕</button>
    </div>
    <div class="menu-section">
        <div class="menu-section-label">Mode</div>
        <button class="mode-btn active" id="tutorModeBtn">💬 Tutor Chat</button>
        <button class="mode-btn" id="paperModeBtn">📝 Generate Paper</button>
    </div>
    <div class="menu-section">
        <div class="menu-section-label">Subject</div>
        <select id="subjectSelect"></select>
    </div>
    <div id="paperSettings" class="menu-section hidden">
        <div class="menu-section-label">Paper Settings</div>
        <select id="paperNum"><option value="1">Paper 1</option><option value="2">Paper 2</option><option value="3">Paper 3</option></select>
        <input type="number" id="totalMarks" value="150" placeholder="Total Marks">
        <input type="number" id="duration" value="3" step="0.5" placeholder="Duration (hours)">
        <input type="text" id="topics" placeholder="Topics (optional, comma separated)">
        <label><input type="checkbox" id="includeMemo" checked> Include Memorandum</label>
        <button class="gen-btn" id="generatePaperBtn">📄 Generate Paper + Memo</button>
    </div>
    <div class="menu-section">
        <div class="menu-section-label">Theme</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <button class="theme-btn" data-theme="light">☀️ Light</button>
            <button class="theme-btn" data-theme="dark">🌙 Dark</button>
            <button class="theme-btn" data-theme="green">🌿 Green</button>
            <button class="theme-btn" data-theme="purple">💜 Purple</button>
        </div>
    </div>
</div>

<div class="main">
    <div class="chat-area" id="chatArea">
        <div class="welcome">
            <strong>Welcome to Zaahir's Tutor! 🎓</strong><br><br>
            <strong>📝 Generate Papers:</strong> Click the ☰ menu → Generate Paper → choose settings → click Generate.<br>
            <strong>✨ Ask About Anything:</strong> Highlight any text in a generated paper → click "Ask Zaahir".<br><br>
            Select your subject in the menu and ask me anything!
        </div>
    </div>
    <div class="input-bar">
        <textarea class="chat-input" id="chatInput" placeholder="Ask me anything..." rows="1"></textarea>
        <button class="send-btn" id="sendBtn">Send</button>
    </div>
</div>

<script>
    // ============================================================
    // MENU FUNCTIONS
    // ============================================================
    const menuPanel = document.getElementById('menuPanel');
    const overlay = document.getElementById('overlay');
    const menuButton = document.getElementById('menuButton');
    const closeMenuBtn = document.getElementById('closeMenuBtn');
    
    function openMenu() {
        menuPanel.classList.add('show');
        overlay.classList.add('show');
    }
    
    function closeMenu() {
        menuPanel.classList.remove('show');
        overlay.classList.remove('show');
    }
    
    menuButton.onclick = openMenu;
    closeMenuBtn.onclick = closeMenu;
    overlay.onclick = closeMenu;
    
    // ============================================================
    // MODE SWITCHING
    // ============================================================
    let currentMode = 'tutor';
    const tutorBtn = document.getElementById('tutorModeBtn');
    const paperBtn = document.getElementById('paperModeBtn');
    const paperSettings = document.getElementById('paperSettings');
    
    tutorBtn.onclick = function() {
        currentMode = 'tutor';
        tutorBtn.classList.add('active');
        paperBtn.classList.remove('active');
        paperSettings.classList.add('hidden');
        closeMenu();
    };
    
    paperBtn.onclick = function() {
        currentMode = 'paper';
        paperBtn.classList.add('active');
        tutorBtn.classList.remove('active');
        paperSettings.classList.remove('hidden');
        closeMenu();
    };
    
    // ============================================================
    // SUBJECTS
    // ============================================================
    async function loadSubjects() {
        const res = await fetch('/subjects');
        const data = await res.json();
        const select = document.getElementById('subjectSelect');
        select.innerHTML = data.subjects.map(s => `<option value="${s}">${s}</option>`).join('');
    }
    
    function getSubject() {
        return document.getElementById('subjectSelect').value;
    }
    
    // ============================================================
    // CHAT FUNCTIONS
    // ============================================================
    let chatHistory = [];
    let selectionToolbar = null;
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
    
    function addMessage(content, type, model) {
        const area = document.getElementById('chatArea');
        const div = document.createElement('div');
        div.className = 'msg ' + type;
        if (type === 'ai') {
            if (content.includes('NATIONAL SENIOR CERTIFICATE') || content.includes('GRADE 12')) {
                div.innerHTML = `<div class="paper-container">${escapeHtml(content)}</div>`;
            } else {
                div.innerHTML = content.replace(/\n/g, '<br>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            }
            if (model) {
                const modelDiv = document.createElement('div');
                modelDiv.className = 'model-tag';
                modelDiv.textContent = 'Model: ' + model;
                div.appendChild(modelDiv);
            }
        } else {
            div.textContent = content;
        }
        area.appendChild(div);
        area.scrollTop = area.scrollHeight;
    }
    
    async function sendMessage() {
        const input = document.getElementById('chatInput');
        const msg = input.value.trim();
        if (!msg) return;
        input.value = '';
        addMessage(msg, 'user');
        chatHistory.push({ role: 'user', content: msg });
        
        const thinking = document.createElement('div');
        thinking.className = 'thinking';
        thinking.textContent = '✦ Thinking...';
        document.getElementById('chatArea').appendChild(thinking);
        
        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    subject: getSubject(),
                    history: chatHistory.slice(-20)
                })
            });
            const data = await res.json();
            thinking.remove();
            addMessage(data.answer, 'ai', data.model_used);
            chatHistory.push({ role: 'assistant', content: data.answer });
        } catch(e) {
            thinking.remove();
            addMessage('Error: Could not reach server.', 'ai');
        }
    }
    
    document.getElementById('sendBtn').onclick = sendMessage;
    document.getElementById('chatInput').onkeydown = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };
    
    // ============================================================
    // TEXT SELECTION (Ask Zaahir)
    // ============================================================
    document.addEventListener('mouseup', function() {
        const sel = window.getSelection();
        const text = sel.toString().trim();
        if (selectionToolbar) {
            selectionToolbar.remove();
            selectionToolbar = null;
        }
        if (text.length > 0 && text.length < 500) {
            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            selectionToolbar = document.createElement('div');
            selectionToolbar.className = 'selection-toolbar';
            selectionToolbar.innerHTML = `<span>📖 Ask Zaahir</span><button onclick="askSelection('${text.replace(/'/g, "\\'")}')">Ask</button>`;
            selectionToolbar.style.position = 'fixed';
            selectionToolbar.style.left = (rect.left + window.scrollX) + 'px';
            selectionToolbar.style.top = (rect.top + window.scrollY - 40) + 'px';
            document.body.appendChild(selectionToolbar);
        }
    });
    
    window.askSelection = async function(text) {
        if (selectionToolbar) {
            selectionToolbar.remove();
            selectionToolbar = null;
        }
        window.getSelection().removeAllRanges();
        addMessage(`📌 You asked about: "${text.substring(0, 100)}"`, 'user');
        
        const thinking = document.createElement('div');
        thinking.className = 'thinking';
        thinking.textContent = '🔍 Zaahir is explaining...';
        document.getElementById('chatArea').appendChild(thinking);
        
        try {
            const res = await fetch('/ask-about-selection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected_text: text,
                    subject: getSubject(),
                    history: chatHistory.slice(-10)
                })
            });
            const data = await res.json();
            thinking.remove();
            addMessage(data.answer, 'ai', data.model_used);
            chatHistory.push({ role: 'assistant', content: data.answer });
        } catch(e) {
            thinking.remove();
            addMessage('Error explaining that section.', 'ai');
        }
    };
    
    // ============================================================
    // PAPER GENERATION
    // ============================================================
    async function generatePaper() {
        const btn = document.getElementById('generatePaperBtn');
        btn.disabled = true;
        btn.textContent = 'Generating...';
        addMessage("📝 **Generating your exam paper...**\n\nCreating an authentic DBE-style paper. This may take 30-60 seconds.", 'ai');
        
        try {
            const res = await fetch('/generate-paper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: getSubject(),
                    paper_number: parseInt(document.getElementById('paperNum').value),
                    total_marks: parseInt(document.getElementById('totalMarks').value),
                    duration_hours: parseFloat(document.getElementById('duration').value),
                    topics: document.getElementById('topics').value.split(',').map(t => t.trim()).filter(Boolean),
                    include_memo: document.getElementById('includeMemo').checked
                })
            });
            const data = await res.json();
            let msg = `📄 **${data.subject} Paper ${data.paper_number}**\n\n**Marks:** ${data.total_marks} | **Duration:** ${data.duration_hours} hours\n\n---\n\n${data.paper}`;
            if (data.memo) msg += `\n\n---\n\n📋 **MEMORANDUM**\n\n${data.memo}`;
            msg += `\n\n---\n\n💡 **Tip:** Highlight any part above and click "Ask Zaahir" for explanation!`;
            addMessage(msg, 'ai', data.model_used);
        } catch(e) {
            addMessage('Error generating paper. Please try again.', 'ai');
        }
        btn.disabled = false;
        btn.textContent = '📄 Generate Paper + Memo';
    }
    
    document.getElementById('generatePaperBtn').onclick = generatePaper;
    
    // ============================================================
    // THEME SWITCHING
    // ============================================================
    function setTheme(theme) {
        const colors = {
            light: { bg: '#f4f6fb', text: '#1a1d2e', header: '#ffffff', border: '#dde2f0', user: '#4a6adc', ai: '#ffffff' },
            dark: { bg: '#0f1117', text: '#e8e8f0', header: '#1a1d2e', border: '#2d3148', user: '#1e2a5e', ai: '#161925' },
            green: { bg: '#0a0f0d', text: '#e0f0e8', header: '#0f1a14', border: '#1e3d2a', user: '#0f2a1e', ai: '#0f1a14' },
            purple: { bg: '#0d0a14', text: '#ede8f8', header: '#160f22', border: '#2d1f48', user: '#2a1a5e', ai: '#160f22' }
        };
        const c = colors[theme];
        document.body.style.background = c.bg;
        document.body.style.color = c.text;
        document.querySelector('.header').style.background = c.header;
        document.querySelector('.input-bar').style.background = c.header;
        document.querySelector('.menu-panel').style.background = c.header;
        document.querySelectorAll('.msg.ai').forEach(el => el.style.background = c.ai);
        document.querySelectorAll('.msg.user').forEach(el => el.style.background = c.user);
        localStorage.setItem('theme', theme);
    }
    
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.onclick = () => setTheme(btn.getAttribute('data-theme'));
    });
    
    // ============================================================
    // INITIALIZE
    // ============================================================
    loadSubjects();
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    console.log('Tutor loaded! Menu should work.');
</script>
</body>
</html>
'''

# ============================================================
# API ENDPOINTS
# ============================================================
@app.get("/")
async def home():
    return HTMLResponse(content=HTML_CONTENT)

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
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
