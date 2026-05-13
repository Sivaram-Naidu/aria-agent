// ─────────────────────────────────────────────
// CONFIG — change this when you deploy to Render
// ─────────────────────────────────────────────
const API_URL = "https://aria-backend-mdge.onrender.com";

// ─────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────
let sessionId       = null;
let isVoiceMode     = false;
let isRecording     = false;
let isSpeaking      = false;
let recognition     = null;
let synth           = window.speechSynthesis;
let ariaVoice       = null;

// ─────────────────────────────────────────────
// DOM ELEMENTS
// ─────────────────────────────────────────────
const chatArea      = document.getElementById("chatArea");
const textInput     = document.getElementById("textInput");
const sendBtn       = document.getElementById("sendBtn");
const voiceBtn      = document.getElementById("voiceBtn");
const voiceToggle   = document.getElementById("voiceToggle");
const statusEl      = document.getElementById("status");
const emotionBadge  = document.getElementById("emotionBadge");
const wakeNotice    = document.getElementById("wakeNotice");

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
async function init() {
    await loadVoice();
    await createSession();
    setupSpeechRecognition();
    showMessage("aria", "Hey! I'm ARIA. What's on your mind?");
}


// ─────────────────────────────────────────────
// SESSION
// ─────────────────────────────────────────────
async function createSession() {
    // Check if session exists in localStorage
    const saved = localStorage.getItem("aria_session_id");

    if (saved) {
        // Verify it's still valid on server
        try {
            const res = await fetch(`${API_URL}/health`);
            if (res.ok) {
                sessionId = saved;
                return;
            }
        } catch (e) {}
    }

    // Create new session
    try {
        wakeNotice.style.display = "block";
        wakeNotice.textContent   = "Waking ARIA up... (first load may take 30s)";

        const res  = await fetch(`${API_URL}/session/new`, { method: "POST" });
        const data = await res.json();

        sessionId = data.session_id;
        localStorage.setItem("aria_session_id", sessionId);
        wakeNotice.style.display = "none";

    } catch (e) {
        wakeNotice.textContent = "Could not connect to ARIA. Is the server running?";
    }
}


// ─────────────────────────────────────────────
// CHAT
// ─────────────────────────────────────────────
async function sendMessage(text) {
    if (!text.trim() || !sessionId) return;

    // Show user bubble
    showMessage("user", text);
    textInput.value = "";
    sendBtn.disabled = true;

    // Show typing indicator
    const typingEl = showTyping();

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        if (res.ok) {
            showMessage("aria", data.response);
            updateEmotion(data.emotion, data.mode);

            // Speak if voice mode
            if (isVoiceMode) {
                speak(data.response);
            }
        } else {
            // Session expired — create new one
            if (res.status === 404) {
                localStorage.removeItem("aria_session_id");
                await createSession();
                showMessage("aria", "Oops, lost our connection! I'm back now though.");
            } else {
                showMessage("aria", "Something went wrong. Try again?");
            }
        }

    } catch (e) {
        typingEl.remove();
        showMessage("aria", "I can't reach the server right now. Is it running?");
    }

    sendBtn.disabled = false;
}


// ─────────────────────────────────────────────
// UI HELPERS
// ─────────────────────────────────────────────
function showMessage(sender, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    const time = document.createElement("div");
    time.className = "timestamp";
    time.textContent = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });

    wrapper.appendChild(bubble);
    wrapper.appendChild(time);
    chatArea.appendChild(wrapper);
    scrollToBottom();

    return wrapper;
}

function showTyping() {
    const wrapper = document.createElement("div");
    wrapper.className = "message aria";

    const typing = document.createElement("div");
    typing.className = "typing";
    typing.innerHTML = "<span></span><span></span><span></span>";

    wrapper.appendChild(typing);
    chatArea.appendChild(wrapper);
    scrollToBottom();

    return wrapper;
}

function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

function updateEmotion(emotion, mode) {
    const icons = {
        HAPPY: "😊 Happy", EXCITED: "🎉 Excited",
        SAD: "💙 Sad",     ANGRY: "😤 Angry",
        ANXIOUS: "😟 Anxious", NEUTRAL: "😐 Neutral"
    };
    const modeIcon = mode === "support" ? "💜" : "✨";

    emotionBadge.textContent = `${modeIcon} ${icons[emotion] || emotion}`;
    emotionBadge.className   = `emotion-badge emotion-${emotion}`;
}


// ─────────────────────────────────────────────
// VOICE INPUT — Web Speech API STT
// ─────────────────────────────────────────────
function setupSpeechRecognition() {
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        voiceBtn.title   = "Voice not supported in this browser";
        voiceBtn.disabled = true;
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang        = "en-IN";  // Indian English
    recognition.continuous  = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        isRecording = true;
        voiceBtn.classList.add("recording");
        voiceBtn.textContent = "⏹️";
        statusEl.textContent = "Listening...";
    };

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        textInput.value  = transcript;
        sendMessage(transcript);
    };

    recognition.onerror = (e) => {
        console.error("Speech error:", e.error);
        statusEl.textContent = "online";
    };

    recognition.onend = () => {
        isRecording = false;
        voiceBtn.classList.remove("recording");
        voiceBtn.textContent = "🎙️";
        statusEl.textContent = "online";
    };
}

function toggleRecording() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}


// ─────────────────────────────────────────────
// VOICE OUTPUT — Web Speech API TTS
// ─────────────────────────────────────────────
async function loadVoice() {
    return new Promise((resolve) => {
        const tryLoad = () => {
            const voices = synth.getVoices();
            // Try to find an Indian English or female voice
            ariaVoice =
                voices.find(v => v.lang === "en-IN") ||
                voices.find(v => v.lang.startsWith("en") && v.name.toLowerCase().includes("female")) ||
                voices.find(v => v.lang.startsWith("en")) ||
                null;
            resolve();
        };

        if (synth.getVoices().length > 0) {
            tryLoad();
        } else {
            synth.onvoiceschanged = tryLoad;
        }
    });
}

function speak(text) {
    if (isSpeaking) synth.cancel();

    const clean = text.replace(/[*#_]/g, "").trim();
    const utt   = new SpeechSynthesisUtterance(clean);

    if (ariaVoice) utt.voice = ariaVoice;
    utt.lang  = "en-IN";
    utt.rate  = 1.0;
    utt.pitch = 1.1;

    utt.onstart = () => { isSpeaking = true; };
    utt.onend   = () => { isSpeaking = false; };

    synth.speak(utt);
}


// ─────────────────────────────────────────────
// EVENT LISTENERS
// ─────────────────────────────────────────────
sendBtn.addEventListener("click", () => {
    sendMessage(textInput.value);
});

textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(textInput.value);
    }
});

voiceBtn.addEventListener("click", toggleRecording);

voiceToggle.addEventListener("change", () => {
    isVoiceMode = voiceToggle.checked;
    voiceBtn.style.display = isVoiceMode ? "flex" : "none";

    if (!isVoiceMode && isSpeaking) {
        synth.cancel();
    }
});

// Clean up session when tab closes
window.addEventListener("beforeunload", () => {
    if (sessionId) {
        navigator.sendBeacon(
            `${API_URL}/session/${sessionId}`,
            JSON.stringify({ _method: "DELETE" })
        );
    }
});

// ─────────────────────────────────────────────
// START
// ─────────────────────────────────────────────
init();
