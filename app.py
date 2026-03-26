<script>
    let mode = 'tutor';
    let chatHistory = [];
    let selectionToolbar = null;

    function setTheme(theme) {
        const colors = {
            light: { bg: '#f4f6fb', text: '#1a1d2e', accent: '#4a6adc', header: '#ffffff', border: '#dde2f0', user: '#4a6adc', ai: '#ffffff' },
            dark: { bg: '#0f1117', text: '#e8e8f0', accent: '#7c9eff', header: '#1a1d2e', border: '#2d3148', user: '#1e2a5e', ai: '#161925' },
            green: { bg: '#0a0f0d', text: '#e0f0e8', accent: '#3ddc84', header: '#0f1a14', border: '#1e3d2a', user: '#0f2a1e', ai: '#0f1a14' },
            purple: { bg: '#0d0a14', text: '#ede8f8', accent: '#b06aff', header: '#160f22', border: '#2d1f48', user: '#2a1a5e', ai: '#160f22' }
        };
        const c = colors[theme];
        document.body.style.background = c.bg;
        document.body.style.color = c.text;
        const headers = document.querySelectorAll('.header, .input-bar');
        headers.forEach(el => { if(el) el.style.background = c.header; });
        document.querySelectorAll('.menu-panel').forEach(el => el.style.background = c.ai);
        document.querySelectorAll('.msg.ai').forEach(el => el.style.background = c.ai);
        document.querySelectorAll('.msg.user').forEach(el => el.style.background = c.user);
        document.querySelectorAll('.menu-select, .menu-input, .chat-input').forEach(el => el.style.background = c.ai);
        localStorage.setItem('theme', theme);
    }

    async function loadSubjects() {
        try {
            const res = await fetch('/subjects');
            const data = await res.json();
            const select = document.getElementById('subject-select');
            if (select) select.innerHTML = data.subjects.map(s => `<option value="${s}">${s}</option>`).join('');
        } catch(e) { console.log(e); }
    }

    function getSubject() { 
        const select = document.getElementById('subject-select');
        return select ? select.value : 'Mathematics';
    }

    function openMenu() { 
        const panel = document.getElementById('menu-panel');
        const overlay = document.getElementById('overlay');
        if (panel) panel.classList.add('open');
        if (overlay) overlay.classList.add('open');
    }
    
    function closeMenu() { 
        const panel = document.getElementById('menu-panel');
        const overlay = document.getElementById('overlay');
        if (panel) panel.classList.remove('open');
        if (overlay) overlay.classList.remove('open');
    }

    function setMode(m) {
        mode = m;
        const tutorBtn = document.getElementById('btn-tutor');
        const paperBtn = document.getElementById('btn-paper');
        const paperSettings = document.getElementById('paper-settings');
        if (tutorBtn) tutorBtn.classList.toggle('active', m === 'tutor');
        if (paperBtn) paperBtn.classList.toggle('active', m === 'paper');
        if (paperSettings) paperSettings.classList.toggle('hidden', m !== 'paper');
    }

    function handleKey(e) { 
        if (e.key === 'Enter' && !e.shiftKey) { 
            e.preventDefault(); 
            sendMessage(); 
        } 
    }

    function escapeHtml(text) { 
        return text.replace(/[&<>]/g, function(m) { 
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]; 
        }); 
    }

    function addMessage(content, type, model) {
        const area = document.getElementById('chat-area');
        if (!area) return;
        const div = document.createElement('div');
        div.className = 'msg ' + type;
        if (type === 'ai') {
            if (content.includes('NATIONAL SENIOR CERTIFICATE')) {
                div.innerHTML = `<div class="paper-container">${escapeHtml(content)}</div>`;
            } else {
                div.innerHTML = content.replace(/\n/g, '<br>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            }
            if (model) { 
                const modelDiv = document.createElement('div');
                modelDiv.style.fontSize = '10px';
                modelDiv.style.color = '#666';
                modelDiv.style.marginTop = '8px';
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
        const input = document.getElementById('chat-input');
        const msg = input.value.trim();
        if (!msg) return;
        input.value = '';
        addMessage(msg, 'user');
        chatHistory.push({ role: 'user', content: msg });
        
        const thinking = document.createElement('div');
        thinking.className = 'thinking';
        thinking.textContent = '✦ Thinking...';
        document.getElementById('chat-area').appendChild(thinking);
        
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

    // Text selection handler
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
            selectionToolbar.innerHTML = `<span>📖 Ask Zaahir</span><button onclick="askSelection('${text.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')">Ask</button>`;
            selectionToolbar.style.position = 'fixed';
            selectionToolbar.style.left = (rect.left + window.scrollX) + 'px';
            selectionToolbar.style.top = (rect.top + window.scrollY - 40) + 'px';
            document.body.appendChild(selectionToolbar);
        }
    });

    async function askSelection(text) {
        if (selectionToolbar) { 
            selectionToolbar.remove(); 
            selectionToolbar = null; 
        }
        addMessage(`📌 Asked about: "${text.substring(0, 100)}"`, 'user');
        
        const thinking = document.createElement('div');
        thinking.className = 'thinking';
        thinking.textContent = '🔍 Zaahir is explaining...';
        document.getElementById('chat-area').appendChild(thinking);
        
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
            addMessage('Error explaining.', 'ai'); 
        }
    }

    async function generatePaper() {
        const btn = document.getElementById('gen-btn');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Generating...';
        }
        addMessage("📝 Generating your exam paper... (30-60 seconds)", 'ai');
        
        try {
            const res = await fetch('/generate-paper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: getSubject(),
                    paper_number: parseInt(document.getElementById('paper-num')?.value || '1'),
                    total_marks: parseInt(document.getElementById('total-marks')?.value || '150'),
                    duration_hours: parseFloat(document.getElementById('duration')?.value || '3'),
                    topics: (document.getElementById('topics')?.value || '').split(',').map(t => t.trim()).filter(Boolean),
                    include_memo: document.getElementById('include-memo')?.checked || true
                })
            });
            const data = await res.json();
            let msg = `📄 **${data.subject} Paper ${data.paper_number}**\n\n**Marks:** ${data.total_marks} | **Duration:** ${data.duration_hours} hours\n\n---\n\n${data.paper}`;
            if (data.memo) msg += `\n\n---\n\n📋 **MEMORANDUM**\n\n${data.memo}`;
            msg += `\n\n---\n\n💡 **Tip:** Highlight any part above and click "Ask Zaahir" for explanation!`;
            addMessage(msg, 'ai', data.model_used);
        } catch(e) { 
            addMessage('Error generating paper.', 'ai'); 
        }
        
        if (btn) {
            btn.disabled = false;
            btn.textContent = '📄 Generate Paper + Memo';
        }
    }

    // Initialize
    loadSubjects();
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
</script>
