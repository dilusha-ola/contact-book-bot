document.addEventListener("DOMContentLoaded", () => {
    console.log("Contact Book Agent Bot UI ready.");
});

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
    appendMessage("user", `Action: ${label}`);
    await sendToAgentBot(label, actionType);

    // Close mobile sidebar if open
    document.getElementById("sidebar").classList.remove("open");
}

async function sendToAgentBot(promptText, actionType = null) {
    // Append loading indicator
    const loadingId = appendLoadingMessage();

    try {
        const payload = {
            prompt: promptText
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
        appendMessage("bot", "⚠️ Connection error. Make sure both Agent Server (Port 8001) and Platform Server (Port 8000) are running.");
    }
}

function appendMessage(sender, text) {
    const chatContainer = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;

    const avatar = sender === 'user' ? '👤' : '🤖';
    const title = sender === 'user' ? 'You' : 'Contact Agent Bot';

    msg.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="message-content">
            <strong>${title}</strong>
            <p>${formatMarkdownText(text)}</p>
        </div>
    `;

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
            <strong>Contact Agent Bot</strong>
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
    document.getElementById("sidebar").classList.toggle("open");
}

function formatMarkdownText(text) {
    if (!text) return '';
    // Basic Markdown Formatting
    let formatted = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    return formatted;
}
