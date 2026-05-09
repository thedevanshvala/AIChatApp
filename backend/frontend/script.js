let currentSessionId = null;
let selectedFile = null;

// ── SVG Icons ─────────────────────────
const ICONS = {
    ai: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 1 4 4v1a1 1 0 0 0 1 1h1a4 4 0 0 1 0 8h-1a1 1 0 0 0-1 1v1a4 4 0 0 1-8 0v-1a1 1 0 0 0-1-1H6a4 4 0 0 1 0-8h1a1 1 0 0 0 1-1V6a4 4 0 0 1 4-4z"/><circle cx="12" cy="12" r="2"/></svg>`,
    user: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    sparkle: `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="url(#sparkleGrad)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><defs><linearGradient id="sparkleGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#818cf8"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient></defs><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z"/><path d="M19 1l.5 2 2 .5-2 .5-.5 2-.5-2-2-.5 2-.5L19 1z" opacity="0.6"/><path d="M4 18l.5 1.5L6 20l-1.5.5L4 22l-.5-1.5L2 20l1.5-.5L4 18z" opacity="0.6"/></svg>`,
    chat: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
};

let username = localStorage.getItem("username");

if (!username) {
    username = prompt("Enter your username");
    if (username) localStorage.setItem("username", username);
}

// Display username in sidebar footer
function updateUsernameDisplay() {
    const el = document.getElementById('sidebarUsername');
    if (el && username) el.textContent = username;
}

document.addEventListener('DOMContentLoaded', updateUsernameDisplay);

// ── Sidebar (mobile) ──────────────────
function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('overlay').classList.add('show');
}
function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
}

// ── Auto-resize textarea ──────────────
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
    const count = document.getElementById('charCount');
    if (count) count.textContent = el.value.length + ' / 4000';
}

// ── File attachment ───────────────────
function handleFileSelect(event) {
    selectedFile = event.target.files[0];
    if (!selectedFile) return;
    const preview = document.getElementById('filePreview');
    const name = document.getElementById('fileName');
    name.textContent = selectedFile.name;
    preview.classList.add('show');
}

function removeFile() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('filePreview').classList.remove('show');
}

// ── Sessions ──────────────────────────
async function loadSessions() {
    try {
        const res = await fetch(`/sessions?username=${username}`);
        const sessions = await res.json();
        const list = document.getElementById('sessionsList');
        list.innerHTML = '';
        sessions.forEach((s, i) => {
            const div = document.createElement('div');
            div.className = `session ${s.id === currentSessionId ? 'active' : ''}`;
            div.style.animationDelay = `${i * 0.04}s`;
            div.innerHTML = `
                <span class="session-icon">${ICONS.chat}</span>
                <span class="session-title" onclick="loadSession(${s.id})">${escapeHtml(s.title)}</span>
                <button class="session-delete" onclick="deleteSession(event, ${s.id})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error('Failed to load sessions:', e);
    }
}

async function newChat() {
    try {
        const res = await fetch('/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: 'New Chat',
                username: username
            })
        });
        const session = await res.json();
        currentSessionId = session.id;
        showWelcome();
        closeSidebar();
        await loadSessions();
    } catch (e) {
        console.error('Failed to create session:', e);
    }
}

async function loadSession(sessionId) {
    currentSessionId = sessionId;
    try {
        const res = await fetch(`/sessions/${sessionId}/messages?username=${username}`)
        const messages = await res.json();
        const container = document.getElementById('messages');
        container.innerHTML = '';
        if (messages.length === 0) {
            showWelcome();
        } else {
            messages.forEach(m => appendMessage(m.role, m.content, false));
            container.scrollTop = container.scrollHeight;
        }
        closeSidebar();
        await loadSessions();
    } catch (e) {
        console.error('Failed to load session:', e);
    }
}

async function deleteSession(event, sessionId) {
    event.stopPropagation();
    try {
        await fetch(`/sessions/${sessionId}`, { method: 'DELETE' });
        if (currentSessionId === sessionId) {
            currentSessionId = null;
            showWelcome();
        }
        await loadSessions();
    } catch (e) {
        console.error('Failed to delete session:', e);
    }
}

// ── Welcome screen ────────────────────
function showWelcome() {
    const container = document.getElementById('messages');
    container.innerHTML = `
        <div class="welcome">
            <div class="welcome-icon">${ICONS.sparkle}</div>
            <h2>Hi ${username ? escapeHtml(username) : 'there'}, what can I help you build?</h2>
            <p>Ask me anything about code — from quick snippets to full architecture. Attach files for code review.</p>
            <div class="suggestions">
                <div class="suggestion" onclick="sendSuggestion('How do I create a REST API in FastAPI?')">
                    <strong>REST API in FastAPI</strong>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Learn how to build modern backends</div>
                </div>
                <div class="suggestion" onclick="sendSuggestion('Explain async/await in Python with examples')">
                    <strong>Async/await in Python</strong>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Understand concurrent programming</div>
                </div>
                <div class="suggestion" onclick="sendSuggestion('How to optimize a slow SQL query?')">
                    <strong>Optimize SQL query</strong>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Improve database performance</div>
                </div>
                <div class="suggestion" onclick="sendSuggestion('What is JWT and how to implement it?')">
                    <strong>JWT authentication</strong>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Secure your applications</div>
                </div>
            </div>
        </div>`;
}

// ── Chat ──────────────────────────────
async function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message && !selectedFile) return;
    if (!currentSessionId) await newChat();

    input.value = '';
    autoResize(input);

    const displayMsg = message + (selectedFile ? ` [${selectedFile.name}]` : '');
    appendMessage('user', displayMsg);
    showTyping();
    document.getElementById('sendBtn').disabled = true;

    try {
        const formData = new FormData();
        formData.append('session_id', currentSessionId);
        formData.append('message', message);
        formData.append("username", username);
        if (selectedFile) formData.append('file', selectedFile);

        const res = await fetch('/chat', { method: 'POST', body: formData });
        const data = await res.json();
        removeTyping();
        appendMessage('assistant', data.response);
        removeFile();
        await loadSessions();
    } catch {
        removeTyping();
        appendMessage('assistant', 'Connection error. Please check your server and try again.');
    }

    document.getElementById('sendBtn').disabled = false;
    input.focus();
}

function appendMessage(role, content, animate = true) {
    const container = document.getElementById('messages');
    const welcome = container.querySelector('.welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = `message ${role}`;
    if (!animate) div.style.animation = 'none';

    const avatar = role === 'user' ? ICONS.user : ICONS.ai;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const html = role === 'assistant'
        ? (typeof marked !== 'undefined' ? marked.parse(content) : `<p>${escapeHtml(content)}</p>`)
        : `<p>${escapeHtml(content)}</p>`;

    div.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div style="display: flex; flex-direction: column; gap: 4px; max-width: 100%; min-width: 0;">
            <div class="bubble">${html}</div>
            <div class="msg-time">${time}</div>
        </div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    // Syntax highlight + copy buttons
    div.querySelectorAll('pre code').forEach(block => {
        if (typeof hljs !== 'undefined') hljs.highlightElement(block);
        addCopyButton(block.closest('pre'));
    });
}

function addCopyButton(pre) {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.onclick = () => {
        navigator.clipboard.writeText(pre.querySelector('code').innerText).then(() => {
            btn.textContent = 'Copied!';
            btn.style.color = '#34d399';
            setTimeout(() => {
                btn.textContent = 'Copy';
                btn.style.color = '';
            }, 2000);
        });
    };
    pre.appendChild(btn);
}

function showTyping() {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'typingIndicator';
    div.innerHTML = `
        <div class="avatar">${ICONS.ai}</div>
        <div class="bubble">
            <div class="typing-bubble"><span></span><span></span><span></span></div>
        </div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTyping() {
    document.getElementById('typingIndicator')?.remove();
}

function sendSuggestion(text) {
    document.getElementById('userInput').value = text;
    autoResize(document.getElementById('userInput'));
    sendMessage();
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function escapeHtml(t) {
    return String(t)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────
loadSessions();