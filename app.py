// ── File Upload with Question ──
let pendingUpload = null; // Store uploaded text until user adds question

async function uploadFile(input) {
  if (!input.files || !input.files[0]) return;
  
  const file = input.files[0];
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', getSubject());
  
  addMessage(`📤 Uploading "${file.name}"...`, 'user');
  
  const thinking = document.createElement('div');
  thinking.className = 'thinking';
  thinking.id = 'upload-thinking';
  thinking.textContent = '🔍 Processing image... extracting text...';
  document.getElementById('chat-area').appendChild(thinking);
  document.getElementById('chat-area').scrollTop = 999999;
  
  try {
    const res = await fetch('/upload', {
      method: 'POST',
      body: formData
    });
    
    const data = await res.json();
    document.getElementById('upload-thinking')?.remove();
    
    if (data.success) {
      // Store the extracted text
      pendingUpload = {
        text: data.extracted_text,
        filename: data.filename
      };
      
      // Show preview and ask for question
      const previewMsg = `✅ **Image uploaded successfully!**\n\n**Extracted text:**\n\`\`\`\n${data.extracted_text_preview}${data.extracted_text.length > 500 ? '\n...(truncated)' : ''}\n\`\`\`\n\n**What would you like me to do with this?**\n\nType your question below (e.g., "Solve this problem" or "Explain step by step") and click Send.`;
      
      addMessage(previewMsg, 'ai');
      
      // Focus the input and add placeholder
      const chatInput = document.getElementById('chat-input');
      chatInput.focus();
      chatInput.placeholder = "Type your question about the image (e.g., 'Solve this', 'Explain step by step')...";
      
    } else {
      addMessage(`❌ Upload failed: ${data.message}\n\n${data.suggestion || 'Try taking a clearer photo with good lighting and make sure the text is in focus.'}`, 'ai');
    }
  } catch (e) {
    document.getElementById('upload-thinking')?.remove();
    addMessage(`❌ Error uploading file. Make sure the server is running.`, 'ai');
  }
  
  input.value = '';
}

