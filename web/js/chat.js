/* 聊天模块 */
let chatHistory = [];
let isStreaming = false;

function toggleChat() {
    const panel = document.getElementById('chatPanel');
    if (panel) {
        panel.classList.toggle('active');
    }
}

async function sendMessage() {
    if (isStreaming) return;
    const input = document.getElementById('chatInput');
    const query = input?.value?.trim();
    if (!query) return;

    input.value = '';

    chatHistory.push({ role: 'user', content: query });
    appendChatMessage('user', query);

    isStreaming = true;
    const sendBtn = document.querySelector('.chat-send-btn');
    if (sendBtn) sendBtn.disabled = true;

    // 添加打字指示器
    const typingId = appendTypingIndicator();

    let fullResponse = '';
    try {
        const es = api.chatStream(query);

        es.onmessage = (event) => {
            if (event.event === 'message') {
                fullResponse += event.data;
                updateLastAssistantMessage(fullResponse);
            } else if (event.event === 'done') {
                removeTypingIndicator(typingId);
                chatHistory.push({ role: 'assistant', content: fullResponse });
                api.saveChatHistory(chatHistory).catch(() => {});
                es.close();
                isStreaming = false;
                if (sendBtn) sendBtn.disabled = false;
            } else if (event.event === 'error') {
                removeTypingIndicator(typingId);
                appendChatMessage('assistant', '抱歉，发生了错误：' + event.data);
                es.close();
                isStreaming = false;
                if (sendBtn) sendBtn.disabled = false;
            }
        };

        es.onerror = () => {
            removeTypingIndicator(typingId);
            es.close();
            isStreaming = false;
            if (sendBtn) sendBtn.disabled = false;
        };
    } catch (e) {
        removeTypingIndicator(typingId);
        appendChatMessage('assistant', '网络错误，请重试。');
        isStreaming = false;
        if (sendBtn) sendBtn.disabled = false;
    }
}

function appendChatMessage(role, content) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;

    const avatar = role === 'user' ? '👤' : '❤️';
    div.innerHTML = `
        <div class="chat-avatar-sm">${avatar}</div>
        <div class="chat-bubble">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function updateLastAssistantMessage(content) {
    const container = document.getElementById('chatMessages');
    const msgs = container.querySelectorAll('.chat-msg.assistant');
    const last = msgs[msgs.length - 1];
    if (last) {
        last.querySelector('.chat-bubble').innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
        container.scrollTop = container.scrollHeight;
    } else {
        appendChatMessage('assistant', content);
    }
}

function appendTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';
    div.id = 'typing-' + Date.now();
    div.innerHTML = `
        <div class="chat-avatar-sm">❤️</div>
        <div class="chat-bubble" style="display:flex;gap:4px;padding:12px">
            <span style="width:8px;height:8px;background:#2D8CFF;border-radius:50%;animation:typingBounce 1s infinite"></span>
            <span style="width:8px;height:8px;background:#2D8CFF;border-radius:50%;animation:typingBounce 1s infinite 0.2s"></span>
            <span style="width:8px;height:8px;background:#2D8CFF;border-radius:50%;animation:typingBounce 1s infinite 0.4s"></span>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 加载历史
async function loadChatHistory() {
    try {
        const data = await api.getChatHistory();
        chatHistory = data.messages || [];
        const container = document.getElementById('chatMessages');
        // 保留第一条欢迎消息
        container.innerHTML = `
            <div class="chat-msg assistant">
                <div class="chat-avatar-sm">❤️</div>
                <div class="chat-bubble">欢迎使用健康智能助手！我可以帮您分析健康数据、提供饮食建议、推荐运动方案。请输入您的问题。</div>
            </div>`;
        chatHistory.forEach(msg => {
            appendChatMessage(msg.role, msg.content);
        });
    } catch (e) {}
}

document.addEventListener('DOMContentLoaded', loadChatHistory);