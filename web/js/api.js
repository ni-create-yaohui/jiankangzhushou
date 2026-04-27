/* API 服务模块 */
const API_BASE = '/api/v1';

const api = {
    // 枚举
    getEnums: () => fetch(`${API_BASE}/enums/all`).then(r => r.json()),

    // 用户
    listUsers: () => fetch(`${API_BASE}/users`).then(r => r.json()),
    getUser: (id) => fetch(`${API_BASE}/users/${id}`).then(r => r.json()),
    createUser: (data) => fetch(`${API_BASE}/users`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
    updateUser: (id, data) => fetch(`${API_BASE}/users/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
    deleteUser: (id) => fetch(`${API_BASE}/users/${id}`, { method: 'DELETE' }).then(r => r.json()),
    addHealthRecord: (id, data) => fetch(`${API_BASE}/users/${id}/health-record`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
    getHealthRecords: (id) => fetch(`${API_BASE}/users/${id}/health-records`).then(r => r.json()),

    // 健康工具
    calculateBMI: (height, weight) => fetch(`${API_BASE}/health/bmi?height=${height}&weight=${weight}`).then(r => r.json()),
    calculateCalorie: (params) => fetch(`${API_BASE}/health/daily-calorie?${new URLSearchParams(params)}`).then(r => r.json()),

    // 报告
    listReports: () => fetch(`${API_BASE}/reports`).then(r => r.json()),
    searchReports: (q) => fetch(`${API_BASE}/reports/search?q=${encodeURIComponent(q)}`).then(r => r.json()),

    // 聊天
    getChatHistory: (sid) => fetch(`${API_BASE}/chat/history${sid ? '?session_id=' + encodeURIComponent(sid) : ''}`).then(r => r.json()),
    saveChatHistory: (messages, sid) => fetch(`${API_BASE}/chat/history${sid ? '?session_id=' + encodeURIComponent(sid) : ''}`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(messages) }).then(r => r.json()),
    clearChatHistory: (sid) => fetch(`${API_BASE}/chat/history${sid ? '?session_id=' + encodeURIComponent(sid) : ''}`, { method: 'DELETE' }).then(r => r.json()),

    // SSE聊天流
    chatStream: (query, sid) => {
        const url = `${API_BASE}/chat/stream?q=${encodeURIComponent(query)}${sid ? '&session_id=' + encodeURIComponent(sid) : ''}`;
        return new EventSource(url);
    },

    // 会话管理
    listSessions: () => fetch(`${API_BASE}/chat/sessions`).then(r => r.json()),
    createSession: () => fetch(`${API_BASE}/chat/sessions`, { method: 'POST' }).then(r => r.json()),
    deleteSession: (sid) => fetch(`${API_BASE}/chat/sessions/${encodeURIComponent(sid)}`, { method: 'DELETE' }).then(r => r.json()),

    // 天气
    getWeather: (city) => fetch(`${API_BASE}/weather?city=${encodeURIComponent(city)}`).then(r => r.json()),
};

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) {
        alert(message);
        return;
    }
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = type === 'error' ? 'border-left:4px solid #F53F3F' : type === 'success' ? 'border-left:4px solid #00B42A' : type === 'warning' ? 'border-left:4px solid #FF7D00' : 'border-left:4px solid #2D8CFF';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
