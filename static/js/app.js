let currentSessionId = "session-" + Date.now();
let chatSessions = [
    { id: currentSessionId, title: "New Chat", messages: [] }
];

document.addEventListener("DOMContentLoaded", () => {
    console.log("Contact Book Agent Bot UI ready.");
    renderChatHistory();
});

function createNewChatSession() {
    currentSessionId = "session-" + Date.now();
    const newSession = {
        id: currentSessionId,
        title: "New Chat",
        messages: []
    };
    chatSessions.unshift(newSession);
    
    // Clear chat stream UI to default welcome message
    const chatContainer = document.getElementById("chat-messages");
    chatContainer.innerHTML = `
        <div class="message bot-message">
            <div class="avatar">🤖</div>
            <div class="message-content">
                <strong>Contact Agent Bot</strong>
                <p>Hello! Started a new chat session. Type a prompt below or click a tool from the right panel!</p>
            </div>
        </div>
    `;

    renderChatHistory();
}

function selectChatSession(sessionId) {
    if (sessionId === 'current') return;
    currentSessionId = sessionId;
    const session = chatSessions.find(s => s.id === sessionId);
    if (!session) return;

    document.getElementById("active-chat-title").innerText = session.title || "Contact Assistant Bot";
    renderChatHistory();
}

function renderChatHistory() {
    const listContainer = document.getElementById("chat-history-list");
    if (!listContainer) return;

    listContainer.innerHTML = "";
    chatSessions.forEach(session => {
        const item = document.createElement("div");
        const isActive = session.id === currentSessionId;
        item.className = `chat-item ${isActive ? 'active' : ''}`;
        item.onclick = () => selectChatSession(session.id);

        item.innerHTML = `
            <span class="chat-item-icon">💬</span>
            <div class="chat-item-info">
                <span class="chat-item-title">${escapeHtml(session.title)}</span>
            </div>
        `;
        listContainer.appendChild(item);
    });
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const prompt = input.value.trim();
    if (!prompt) return;

    // Set thread title if first message
    const activeSession = chatSessions.find(s => s.id === currentSessionId);
    if (activeSession && (activeSession.title === "New Chat" || !activeSession.title)) {
        activeSession.title = prompt.length > 25 ? prompt.substring(0, 25) + "..." : prompt;
        renderChatHistory();
    }

    appendMessage("user", prompt);
    input.value = "";

    await sendToAgentBot(prompt);
}

async function triggerQuickAction(actionType, label) {
    appendMessage("user", label);
    await sendToAgentBot(label, actionType);

    // Close mobile left sidebar if open
    const sidebarLeft = document.getElementById("sidebar-left");
    if (sidebarLeft) sidebarLeft.classList.remove("open");
}

async function sendToAgentBot(promptText, actionType = null) {
    const loadingId = appendLoadingMessage();

    try {
        const payload = {
            prompt: promptText,
            session_id: currentSessionId
        };
        if (actionType) {
            payload.action = actionType;
        }

        const res = await fetch("/api/v1/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        removeLoadingMessage(loadingId);

        if (res.ok) {
            const data = await res.json();
            appendMessage("bot", data.reply);
        } else {
            appendMessage("bot", "⚠️ Could not communicate with Agent Server.");
        }
    } catch (err) {
        removeLoadingMessage(loadingId);
        appendMessage("bot", "⚠️ Connection error. Make sure Agent Server (Port 8001) and Platform (Port 8000) are running.");
    }
}

function appendMessage(sender, text) {
    const chatContainer = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;

    const avatar = sender === 'user' ? '👤' : '🤖';

    if (sender === 'user') {
        msg.innerHTML = `
            <div class="message-content">
                <p>${formatMarkdownText(text)}</p>
            </div>
            <div class="avatar">${avatar}</div>
        `;
    } else {
        msg.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-header">Contact Agent Bot</div>
                <p>${formatMarkdownText(text)}</p>
            </div>
        `;
    }

    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendLoadingMessage() {
    const chatContainer = document.getElementById("chat-messages");
    const id = "loading-" + Date.now();
    const msg = document.createElement("div");
    msg.className = "message bot-message";
    msg.id = id;
    msg.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="message-content">
            <div class="message-header">Contact Agent Bot</div>
            <p style="color: var(--text-muted);">Thinking & connecting to Platform API...</p>
        </div>
    `;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
}

function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function toggleMobileMenu() {
    const sidebarLeft = document.getElementById("sidebar-left");
    if (sidebarLeft) sidebarLeft.classList.toggle("open");
}

function formatMarkdownText(text) {
    if (!text) return '';
    let formatted = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    return formatted;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
