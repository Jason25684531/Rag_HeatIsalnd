document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');

    let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    function addMessage(sender, text, isHtml = false) { // 新增 isHtml 參數
        let messageElement = document.createElement('div');
        messageElement.classList.add('mb-3', 'p-3', 'rounded-lg', 'max-w-prose', 'break-words');
        
        // --- 【修正處 1】---
        // 增加 message-content 容器，以利於樣式控制
        const contentContainer = document.createElement('div');
        contentContainer.classList.add('message-content');


        if (sender === 'user') {
            messageElement.classList.add('bg-blue-100', 'ml-auto');
            contentContainer.textContent = text;
        } else {
            messageElement.classList.add('bg-gray-100', 'mr-auto');
            // 如果是 HTML (已處理過的 Markdown)，則使用 innerHTML
            if (isHtml) {
                contentContainer.innerHTML = `<span class="font-semibold">AI:</span> ${text}`;
            } else {
                contentContainer.innerHTML = '<span class="font-semibold">AI:</span> <div class="thinking-indicator"><span>.</span><span>.</span><span>.</span></div>';
            }
        }
        
        messageElement.appendChild(contentContainer);
        chatWindow.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageElement;
    }

    async function handleSendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        addMessage('user', message);
        messageInput.value = '';

        const aiMessageElement = addMessage('ai', '', false);
        let fullResponseMarkdown = "";

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, session_id: sessionId })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            const contentContainer = aiMessageElement.querySelector('.message-content');
            contentContainer.innerHTML = '<span class="font-semibold">AI:</span> '; // 清除等待指示器

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                fullResponseMarkdown += decoder.decode(value, {stream: true});
                
                // --- 【修正處 2】---
                // 將累積的 Markdown 文本轉換為 HTML 並顯示
                const htmlContent = marked.parse(fullResponseMarkdown);
                contentContainer.innerHTML = `<span class="font-semibold">AI:</span> ${htmlContent}`;
                
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }
        } catch (error) {
            console.error('Error:', error);
            const contentContainer = aiMessageElement.querySelector('.message-content');
            contentContainer.innerHTML = `<span class="font-semibold">AI:</span> 抱歉，發生錯誤了。`;
        }
    }

    sendBtn.addEventListener('click', handleSendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSendMessage();
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) {
            uploadStatus.textContent = "請選擇一個文件。";
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        uploadStatus.textContent = `正在上傳 ${file.name}...`;

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (response.ok) {
                uploadStatus.textContent = result.message;
            } else {
                uploadStatus.textContent = `錯誤: ${result.error}`;
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadStatus.textContent = "上傳失敗，請檢查後端服務。";
        }
    });
});
