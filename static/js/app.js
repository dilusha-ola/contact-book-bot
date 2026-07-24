let currentSessionId = "session-" + Date.now();
let chatSessions = [];

document.addEventListener("DOMContentLoaded", async () => {
    console.log("Contact Book Agent Bot UI ready.");
    await fetchChatSessions();
    // Default to the first session if history exists
    if (chatSessions.length > 0) {
        selectChatSession(chatSessions[0].session_id);
    } else {
        createNewChatSession();
    }
});

async function fetchChatSessions() {
    try {
        const res = await fetch("/api/v1/chat/sessions");
        if (res.ok) {
            chatSessions = await res.json();
        }
    } catch (err) {
        console.error("Error loading chat sessions:", err);
    }
    renderChatHistory();
}

function createNewChatSession() {
    const newSessionId = "session-" + Date.now();
    currentSessionId = newSessionId;
    
    // Add pending new chat to top of list if not already present
    const existing = chatSessions.find(s => s.session_id === newSessionId);
    if (!existing) {
        chatSessions.unshift({
            session_id: newSessionId,
            title: "New Chat",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            is_new: true
        });
    }

    renderWelcomeMessage();
    document.getElementById("active-chat-title").innerText = "New Chat";
    renderChatHistory();
}

function renderWelcomeMessage() {
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
}

async function selectChatSession(sessionId) {
    currentSessionId = sessionId;
    renderChatHistory();

    const session = chatSessions.find(s => s.session_id === sessionId);
    if (session) {
        document.getElementById("active-chat-title").innerText = session.title || "Contact Assistant Bot";
    }

    // If it's an uncommitted new session with no messages yet
    if (session && session.is_new) {
        renderWelcomeMessage();
        return;
    }

    try {
        const res = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`);
        if (res.ok) {
            const messages = await res.json();
            renderSessionMessages(messages);
        }
    } catch (err) {
        console.error("Error loading session messages:", err);
    }
}

function renderSessionMessages(messages) {
    const chatContainer = document.getElementById("chat-messages");
    chatContainer.innerHTML = "";

    if (!messages || messages.length === 0) {
        renderWelcomeMessage();
        return;
    }

    messages.forEach(msg => {
        appendMessage(msg.role, msg.content);
    });
}

function renderChatHistory() {
    const listContainer = document.getElementById("chat-history-list");
    if (!listContainer) return;

    listContainer.innerHTML = "";
    if (chatSessions.length === 0) {
        listContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 12px; padding: 8px;">No previous chats.</p>`;
        return;
    }

    chatSessions.forEach(session => {
        const item = document.createElement("div");
        const isActive = session.session_id === currentSessionId;
        item.className = `chat-item ${isActive ? 'active' : ''}`;
        
        item.innerHTML = `
            <span class="chat-item-icon">💬</span>
            <div class="chat-item-info" onclick="selectChatSession('${session.session_id}')">
                <span class="chat-item-title">${escapeHtml(session.title)}</span>
            </div>
            <div class="chat-item-actions">
                <button class="btn-action-icon" title="Rename Title" onclick="renameChatSession('${session.session_id}', event)">✏️</button>
                <button class="btn-action-icon btn-delete" title="Delete Chat" onclick="deleteChatSession('${session.session_id}', event)">🗑️</button>
            </div>
        `;
        listContainer.appendChild(item);
    });
}

async function renameChatSession(sessionId, event) {
    event.stopPropagation();
    const session = chatSessions.find(s => s.session_id === sessionId);
    const currentTitle = session ? session.title : "New Chat";
    
    const newTitle = prompt("Enter new title for this chat session:", currentTitle);
    if (!newTitle || newTitle.trim() === "" || newTitle === currentTitle) return;

    try {
        const res = await fetch(`/api/v1/chat/sessions/${sessionId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: newTitle.trim() })
        });
        if (res.ok) {
            await fetchChatSessions();
            if (currentSessionId === sessionId) {
                document.getElementById("active-chat-title").innerText = newTitle.trim();
            }
        } else {
            alert("Failed to rename chat title");
        }
    } catch (err) {
        console.error("Error renaming chat session:", err);
    }
}

async function deleteChatSession(sessionId, event) {
    event.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat session?")) return;

    try {
        const res = await fetch(`/api/v1/chat/sessions/${sessionId}`, { method: "DELETE" });
        if (res.ok) {
            chatSessions = chatSessions.filter(s => s.session_id !== sessionId);
            if (currentSessionId === sessionId) {
                if (chatSessions.length > 0) {
                    selectChatSession(chatSessions[0].session_id);
                } else {
                    createNewChatSession();
                }
            } else {
                renderChatHistory();
            }
        } else {
            alert("Failed to delete chat session");
        }
    } catch (err) {
        console.error("Error deleting session:", err);
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const prompt = input.value.trim();
    if (!prompt) return;

    appendMessage("user", prompt);
    input.value = "";

    await sendToAgentBot(prompt);
}

async function triggerQuickAction(actionType, label) {
    appendMessage("user", label);
    await sendToAgentBot(label, actionType);

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
            if (data.session_id) {
                currentSessionId = data.session_id;
            }
            appendMessage("bot", data.reply);

            // Refresh sessions list to update smart title from MongoDB
            await fetchChatSessions();
            const session = chatSessions.find(s => s.session_id === currentSessionId);
            if (session) {
                document.getElementById("active-chat-title").innerText = session.title;
            }
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
