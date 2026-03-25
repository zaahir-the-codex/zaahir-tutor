<!DOCTYPE html>
<html>
<head>
    <title>Zaahir's Tutor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .chat-area { background: white; border-radius: 10px; padding: 20px; min-height: 400px; margin-bottom: 20px; }
        .input-area { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #4a6adc; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .message { margin-bottom: 10px; padding: 10px; border-radius: 5px; }
        .user { background: #e3f2fd; text-align: right; }
        .ai { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>Zaahir's Grade 12 Tutor</h1>
    <div class="chat-area" id="chat-area"></div>
    <div class="input-area">
        <input type="text" id="message" placeholder="Ask me anything..." onkeypress="handleKey(event)">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('message');
            const msg = input.value.trim();
            if (!msg) return;
            
            addMessage(msg, 'user');
            input.value = '';
            
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg, subject: 'Mathematics', history: []})
                });
                const data = await res.json();
                addMessage(data.answer, 'ai');
            } catch(e) {
                addMessage('Error: ' + e.message, 'ai');
            }
        }
        
        function addMessage(text, type) {
            const area = document.getElementById('chat-area');
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            area.appendChild(div);
            area.scrollTop = area.scrollHeight;
        }
        
        function handleKey(e) {
            if (e.key === 'Enter') sendMessage();
        }
        
        addMessage("Welcome to Zaahir's Tutor! Ask me anything about Grade 12 subjects.", 'ai');
    </script>
</body>
</html>
