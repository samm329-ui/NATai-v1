/* ================================================================
   N.A.T. (Natasha) Frontend — Main Application Logic
   ================================================================ */

/*
 * API — The base URL for all backend requests.
 */
const API = (typeof window !== 'undefined' && window.location.origin)
    ? window.location.origin
    : 'http://localhost:8000';

/* ================================================================
   APPLICATION STATE
   ================================================================ */
let sessionId = null;
let currentMode = 'general';
let isStreaming = false;
let isListening = false;
let orb = null;
let recognition = null;
let ttsPlayer = null;

const $ = id => document.getElementById(id);

const chatMessages = $('chat-messages');
const messageInput = $('message-input');
const sendBtn      = $('send-btn');
const micBtn       = $('mic-btn');
const ttsBtn       = $('tts-btn');
const newChatBtn   = $('new-chat-btn');
const modeLabel    = $('mode-label');
const charCount    = $('char-count');
const welcomeTitle = $('welcome-title');
const modeSlider   = $('mode-slider');
const btnGeneral   = $('btn-general');
const btnRealtime  = $('btn-realtime');
const statusDot    = document.querySelector('.status-dot');
const statusText   = document.querySelector('.status-text');
const orbContainer = $('orb-container');
const searchResultsToggle = $('search-results-toggle');
const searchResultsWidget = $('search-results-widget');
const searchResultsClose  = $('search-results-close');
const searchResultsQuery  = $('search-results-query');
const searchResultsAnswer = $('search-results-answer');
const searchResultsList   = $('search-results-list');
const pauseBtn           = $('pause-btn');

let currentController = null;

/* ================================================================
   TTS AUDIO PLAYER
   ================================================================ */
class TTSPlayer {
    constructor() {
        this.queue = [];
        this.playing = false;
        this.enabled = true; 
        this.stopped = false;
        this.audio = document.createElement('audio');
        this.audio.preload = 'auto';
    }

    unlock() {
        const silentWav = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
        this.audio.src = silentWav;
        const p = this.audio.play();
        if (p) p.catch(() => {});
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const g = ctx.createGain();
            g.gain.value = 0;
            const o = ctx.createOscillator();
            o.connect(g);
            g.connect(ctx.destination);
            o.start(0);
            o.stop(ctx.currentTime + 0.001);
            setTimeout(() => ctx.close(), 200);
        } catch (_) {}
    }

    enqueue(base64Audio) {
        if (!this.enabled || this.stopped) return;
        this.queue.push(base64Audio);
        if (!this.playing) this._playLoop();
    }

    stop() {
        this.stopped = true;
        this.audio.pause();
        this.audio.removeAttribute('src');
        this.audio.load();
        this.queue = [];
        this.playing = false;
        if (ttsBtn) ttsBtn.classList.remove('tts-speaking');
        if (orbContainer) orbContainer.classList.remove('speaking');
        if (orb) orb.setActive(false);
    }

    reset() {
        this.stop();
        this.stopped = false;
    }

    async _playLoop() {
        if (this.playing) return;
        this.playing = true;
        this._loopId = (this._loopId || 0) + 1;
        const myId = this._loopId;

        if (ttsBtn) ttsBtn.classList.add('tts-speaking');
        if (orbContainer) orbContainer.classList.add('speaking');
        if (orb) orb.setActive(true);

        while (this.queue.length > 0) {
            if (this.stopped || myId !== this._loopId) break;
            const b64 = this.queue.shift();
            try {
                await this._playB64(b64);
            } catch (e) {
                console.warn('TTS segment error:', e);
            }
        }

        if (myId !== this._loopId) return;
        this.playing = false;
        if (ttsBtn) ttsBtn.classList.remove('tts-speaking');
        if (orbContainer) orbContainer.classList.remove('speaking');
        if (orb) orb.setActive(false);
    }

    _playB64(b64) {
        return new Promise(resolve => {
            this.audio.src = 'data:audio/mp3;base64,' + b64;
            const done = () => { resolve(); };
            this.audio.onended = done;
            this.audio.onerror = done;
            const p = this.audio.play();
            if (p) p.catch(done);
        });
    }
}

/* ================================================================
   INITIALIZATION
   ================================================================ */
function init() {
    ttsPlayer = new TTSPlayer();
    if (ttsBtn) ttsBtn.classList.add('tts-active');
    setGreeting();
    initOrb();
    initSpeech();
    checkHealth();
    bindEvents();
    autoResizeInput();
}

function setGreeting() {
    const h = new Date().getHours();
    let g = 'Good evening, Boss.';
    if (h < 12) g = 'Good morning, Boss.';
    else if (h < 17) g = 'Good afternoon, Boss.';
    else if (h >= 22) g = 'Late night, Boss?';
    welcomeTitle.textContent = g;
}

function initOrb() {
    if (typeof OrbRenderer === 'undefined') return;
    try {
        orb = new OrbRenderer(orbContainer, {
            hue: 280, // Purple/Pink hue for Natasha
            hoverIntensity: 0.3,
            backgroundColor: [0.02, 0.02, 0.06]
        });
    } catch (e) { console.warn('Orb init failed:', e); }
}

/* ================================================================
   SPEECH RECOGNITION
   ================================================================ */
function initSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { 
        console.log('Speech Recognition not supported');
        micBtn.title = 'Speech not supported in this browser';
        micBtn.disabled = true;
        return; 
    }

    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    // iOS Safari specific
    recognition.grammars = null;

    recognition.onresult = e => {
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
                transcript += e.results[i][0].transcript;
            }
        }
        
        if (!transcript) {
            transcript = e.results[e.results.length - 1][0].transcript;
        }
        
        if (transcript) {
            messageInput.value = transcript;
            autoResizeInput();
        }
        
        if (e.results[e.results.length - 1].isFinal) {
            const finalText = messageInput.value.trim();
            stopListening();
            if (finalText) {
                sendMessage(finalText);
            }
        }
    };
    
    recognition.onerror = e => {
        console.error('Speech error:', e.error);
        if (e.error === 'network') {
            alert('Voice requires internet. Try using keyboard instead.');
        } else if (e.error === 'not-allowed') {
            alert('Please allow microphone access in browser settings.');
        }
        stopListening();
    };
    
    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove('listening');
    };
}

function startListening() {
    if (!recognition || isStreaming) return;
    if (isListening) return;
    
    messageInput.value = '';
    isListening = true;
    micBtn.classList.add('listening');
    
    try {
        recognition.start();
    } catch(e) {
        console.error('Start error:', e);
        isListening = false;
        micBtn.classList.remove('listening');
    }
}

function stopListening() {
    isListening = false;
    micBtn.classList.remove('listening');
    if (recognition) {
        try { recognition.stop(); } catch(e) {}
    }
}

async function checkHealth() {
    try {
        const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) });
        const d = await r.json();
        const ok = d.status === 'healthy';
        statusDot.classList.toggle('offline', !ok);
        statusText.textContent = ok ? 'Online' : 'Offline';
        if (!ok) {
            console.error('Server health check failed:', d);
        }
    } catch (e) {
        console.error('Health check failed:', e);
        statusDot.classList.add('offline');
        statusText.textContent = 'Offline';
    }
}

function bindEvents() {
    sendBtn.addEventListener('click', () => { if (!isStreaming) sendMessage(); });
    messageInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (!isStreaming) sendMessage(); }
    });
    messageInput.addEventListener('input', () => {
        autoResizeInput();
        const len = messageInput.value.length;
        charCount.textContent = len > 100 ? `${len.toLocaleString()} / 32,000` : '';
    });
    micBtn.addEventListener('click', () => { isListening ? stopListening() : startListening(); });
    ttsBtn.addEventListener('click', () => {
        ttsPlayer.enabled = !ttsPlayer.enabled;
        ttsBtn.classList.toggle('tts-active', ttsPlayer.enabled);
        if (!ttsPlayer.enabled) ttsPlayer.stop();
    });
    pauseBtn.addEventListener('click', stopStreaming);
    newChatBtn.addEventListener('click', newChat);
    btnGeneral.addEventListener('click',  () => setMode('general'));
    btnRealtime.addEventListener('click', () => setMode('realtime'));
    document.querySelectorAll('.chip').forEach(c => {
        c.addEventListener('click', () => { if (!isStreaming) sendMessage(c.dataset.msg); });
    });
    if (searchResultsToggle) {
        searchResultsToggle.addEventListener('click', () => {
            if (searchResultsWidget) searchResultsWidget.classList.add('open');
        });
    }
    if (searchResultsClose && searchResultsWidget) {
        searchResultsClose.addEventListener('click', () => searchResultsWidget.classList.remove('open'));
    }
}

function autoResizeInput() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

function setMode(mode) {
    currentMode = mode;
    btnGeneral.classList.toggle('active', mode === 'general');
    btnRealtime.classList.toggle('active', mode === 'realtime');
    modeSlider.classList.toggle('right', mode === 'realtime');
    modeLabel.textContent = mode === 'general' ? 'General Mode' : 'Realtime Mode';
    if (searchResultsToggle) {
        searchResultsToggle.style.display = (mode === 'realtime') ? '' : 'none';
    }
    if (searchResultsWidget) {
        searchResultsWidget.classList.remove('open');
    }
}

function newChat() {
    if (ttsPlayer) ttsPlayer.stop();
    sessionId = null;
    chatMessages.innerHTML = '';
    chatMessages.appendChild(createWelcome());
    messageInput.value = '';
    autoResizeInput();
    setGreeting();
    if (searchResultsWidget) searchResultsWidget.classList.remove('open');
    if (searchResultsToggle) searchResultsToggle.style.display = 'none';
}

function createWelcome() {
    const h = new Date().getHours();
    let g = 'Good evening, Boss.';
    if (h < 12) g = 'Good morning, Boss.';
    else if (h < 17) g = 'Good afternoon, Boss.';
    else if (h >= 22) g = 'Late night, Boss?';

    const div = document.createElement('div');
    div.className = 'welcome-screen';
    div.id = 'welcome-screen';
    div.innerHTML = `
        <div class="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <h2 class="welcome-title">${g}</h2>
        <p class="welcome-sub">I am Natasha. How may I assist you today?</p>
        <div class="welcome-chips">
            <button class="chip" data-msg="Who are you?">Who are you?</button>
            <button class="chip" data-msg="Check the latest tech news">Latest News</button>
            <button class="chip" data-msg="Tell me a fun fact">Fun fact</button>
            <button class="chip" data-msg="Analyze my business data">Business Intelligence</button>
        </div>`;

    div.querySelectorAll('.chip').forEach(c => {
        c.addEventListener('click', () => { if (!isStreaming) sendMessage(c.dataset.msg); });
    });
    return div;
}

/* ================================================================
   MESSAGE RENDERING
   ================================================================ */
function isUrlLike(str) {
    if (!str || typeof str !== 'string') return false;
    const s = str.trim();
    return s.length > 40 && (/^https?:\/\//i.test(s) || /\%2f|\%3a|\.com\/|\.org\//i.test(s));
}

function friendlyUrlLabel(url) {
    if (!url || typeof url !== 'string') return 'View source';
    try {
        const u = new URL(url.startsWith('http') ? url : 'https://' + url);
        const host = u.hostname.replace(/^www\./, '');
        const path = u.pathname !== '/' ? u.pathname.slice(0, 20) + (u.pathname.length > 20 ? '…' : '') : '';
        return path ? host + path : host;
    } catch (_) {
        return url.length > 40 ? url.slice(0, 37) + '…' : url;
    }
}

function truncateSnippet(text, maxLen) {
    if (!text || typeof text !== 'string') return '';
    const t = text.trim();
    if (t.length <= maxLen) return t;
    return t.slice(0, maxLen).trim() + '…';
}

function renderSearchResults(payload) {
    if (!payload) return;
    if (searchResultsQuery) searchResultsQuery.textContent = (payload.query || '').trim() || 'Search';
    if (searchResultsAnswer) searchResultsAnswer.textContent = (payload.answer || '').trim() || '';
    if (!searchResultsList) return;
    searchResultsList.innerHTML = '';
    const results = payload.results || [];
    const maxContentLen = 220;
    for (const r of results) {
        let title = (r.title || '').trim();
        let content = (r.content || '').trim();
        const url = (r.url || '').trim();
        if (isUrlLike(title)) title = friendlyUrlLabel(url) || 'Source';
        if (!title) title = friendlyUrlLabel(url) || 'Source';
        if (isUrlLike(content)) content = '';
        content = truncateSnippet(content, maxContentLen);
        const score = r.score != null ? Math.round((r.score || 0) * 100) : null;
        const card = document.createElement('div');
        card.className = 'search-result-card';
        const urlDisplay = url ? escapeHtml(friendlyUrlLabel(url)) : '';
        const urlSafe = url ? url.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
        card.innerHTML = `
            <div class="card-title">${escapeHtml(title)}</div>
            ${content ? `<div class="card-content">${escapeHtml(content)}</div>` : ''}
            ${url ? `<a href="${urlSafe}" target="_blank" rel="noopener" class="card-url" title="${escapeAttr(url)}">${urlDisplay}</a>` : ''}
            ${score != null ? `<div class="card-score">Relevance: ${escapeHtml(String(score))}%</div>` : ''}`;
        searchResultsList.appendChild(card);
    }
}

function escapeAttr(str) {
    if (typeof str !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML.replace(/"/g, '&quot;');
}

function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function hideWelcome() {
    const w = document.getElementById('welcome-screen');
    if (w) w.remove();
}

const AVATAR_ICON_USER = '<svg class="msg-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
const AVATAR_ICON_ASSISTANT = '<svg class="msg-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><circle cx="9" cy="16" r="1" fill="currentColor"/><circle cx="15" cy="16" r="1" fill="currentColor"/></svg>';

function addMessage(role, text) {
    hideWelcome();
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = role === 'assistant' ? AVATAR_ICON_ASSISTANT : AVATAR_ICON_USER;

    const body = document.createElement('div');
    body.className = 'msg-body';

    const label = document.createElement('div');
    label.className = 'msg-label';
    label.textContent = role === 'assistant'
        ? `Natasha (${currentMode === 'realtime' ? 'Realtime' : 'General'})`
        : 'You';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.textContent = text;

    body.appendChild(label);
    body.appendChild(content);
    msg.appendChild(avatar);
    msg.appendChild(body);
    chatMessages.appendChild(msg);
    scrollToBottom();
    return content;
}

function addTypingIndicator() {
    hideWelcome();
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.id = 'typing-msg';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = AVATAR_ICON_ASSISTANT;

    const body = document.createElement('div');
    body.className = 'msg-body';

    const label = document.createElement('div');
    label.className = 'msg-label';
    label.textContent = `Natasha (${currentMode === 'realtime' ? 'Realtime' : 'General'})`;

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';

    body.appendChild(label);
    body.appendChild(content);
    msg.appendChild(avatar);
    msg.appendChild(body);
    chatMessages.appendChild(msg);
    scrollToBottom();
    return content;
}

function removeTypingIndicator() {
    const t = document.getElementById('typing-msg');
    if (t) t.remove();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

/* ================================================================
   SEND MESSAGE + SSE STREAMING
   ================================================================ */
async function sendMessage(textOverride) {
    const text = (textOverride || messageInput.value).trim();
    if (!text || isStreaming) return;

    messageInput.value = '';
    autoResizeInput();
    charCount.textContent = '';

    addMessage('user', text);
    addTypingIndicator();

    isStreaming = true;
    sendBtn.disabled = true;
    pauseBtn.style.display = 'flex';

    if (ttsPlayer) { ttsPlayer.reset(); ttsPlayer.unlock(); }

    const endpoint = currentMode === 'realtime' ? '/chat/realtime/stream' : '/chat/stream';
    currentController = new AbortController();

    try {
        const res = await fetch(`${API}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: sessionId,
                tts: !!(ttsPlayer && ttsPlayer.enabled)
            }),
            signal: currentController.signal
        });

        if (!res.ok) {
            const err = await res.json().catch(() => null);
            throw new Error(err?.detail || `HTTP ${res.status}`);
        }

        removeTypingIndicator();
        const contentEl = addMessage('assistant', '');
        const placeholder = currentMode === 'realtime' ? 'Searching...' : 'Thinking...';
        contentEl.innerHTML = `<span class="msg-stream-text">${placeholder}</span>`;
        scrollToBottom();

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let sseBuffer = '';
        let fullResponse = '';
        let cursorEl = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            sseBuffer += decoder.decode(value, { stream: true });
            const lines = sseBuffer.split('\n');
            sseBuffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.session_id) sessionId = data.session_id;

                    if (data.search_results) {
                        renderSearchResults(data.search_results);
                        if (searchResultsToggle) searchResultsToggle.style.display = '';
                        if (searchResultsWidget) searchResultsWidget.classList.add('open');
                    }

                    if (data.chunk) {
                        fullResponse += data.chunk;
                        const textSpan = contentEl.querySelector('.msg-stream-text');
                        if (textSpan) textSpan.textContent = fullResponse;

                        if (!cursorEl) {
                            cursorEl = document.createElement('span');
                            cursorEl.className = 'stream-cursor';
                            cursorEl.textContent = '|';
                            contentEl.appendChild(cursorEl);
                        }
                        scrollToBottom();
                    }

                    if (data.audio && ttsPlayer) {
                        ttsPlayer.enqueue(data.audio);
                    }

                    if (data.error) throw new Error(data.error);
                    if (data.done) break;
                } catch (parseErr) {
                    if (parseErr.message && !parseErr.message.includes('JSON'))
                        throw parseErr;
                }
            }
        }

        if (cursorEl) cursorEl.remove();
        const textSpan = contentEl.querySelector('.msg-stream-text');
        if (textSpan && !fullResponse) textSpan.textContent = '(No response)';

} catch (err) {
        if (err.name === 'AbortError') {
            removeTypingIndicator();
            addMessage('assistant', 'Response paused.');
        } else {
            removeTypingIndicator();
            addMessage('assistant', `Something went wrong: ${err.message}`);
        }
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        pauseBtn.style.display = 'none';
        currentController = null;
    }
}

function stopStreaming() {
    if (currentController) {
        currentController.abort();
    }
    if (ttsPlayer) {
        ttsPlayer.stop();
    }
}

document.addEventListener('DOMContentLoaded', init);