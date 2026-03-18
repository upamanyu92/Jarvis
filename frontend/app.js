/**
 * Jarvis – Emotion-Aware AI Companion
 * Frontend application logic
 */

// ── Service URLs (set via nginx proxy in Docker; defaults for local dev) ──
const API = {
  vision:  window.VISION_URL  || '/api/vision',
  speech:  window.SPEECH_URL  || '/api/speech',
  agent:   window.AGENT_URL   || '/api/agent',
  tts:     window.TTS_URL     || '/api/tts',
};

// ── State ──
let userId        = localStorage.getItem('jarvis_user_id') || `user_${Date.now()}`;
let currentEmotion = 'neutral';
let webcamStream  = null;
let mediaRecorder = null;
let audioChunks   = [];
let isRecording   = false;
let emotionInterval = null;

localStorage.setItem('jarvis_user_id', userId);

// ── DOM references ──
const webcamVideo      = document.getElementById('webcamVideo');
const webcamCanvas     = document.getElementById('webcamCanvas');
const emotionLabel     = document.getElementById('emotionLabel');
const emotionFill      = document.getElementById('emotionFill');
const btnStartCam      = document.getElementById('btnStartCam');
const btnStopCam       = document.getElementById('btnStopCam');
const btnSend          = document.getElementById('btnSend');
const btnRecord        = document.getElementById('btnRecord');
const userInput        = document.getElementById('userInput');
const chatMessages     = document.getElementById('chatMessages');
const audioPlayer      = document.getElementById('audioPlayer');
const recordingIndicator = document.getElementById('recordingIndicator');
const statusVision     = document.getElementById('statusVision');
const statusSpeech     = document.getElementById('statusSpeech');
const statusAgent      = document.getElementById('statusAgent');
const sidebarToggle    = document.getElementById('sidebarToggle');
const sidebarContent   = document.getElementById('sidebarContent');
const userName         = document.getElementById('userName');
const btnSaveName      = document.getElementById('btnSaveName');
const emotionHistoryEl = document.getElementById('emotionHistory');

// ── Emotion emoji map ──
const EMOTION_EMOJI = {
  happy:    '😄', sad:      '😢', angry:   '😠',
  fear:     '😨', surprise: '😲', disgust: '🤢',
  neutral:  '😐', contempt: '😒',
};

// ── Utility ──
function getEmoji(emotion) {
  return EMOTION_EMOJI[emotion] || '😐';
}

function setStatus(el, active, label) {
  el.textContent = label;
  el.classList.toggle('active', active);
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── Chat message rendering ──
function appendMessage(role, text, emotion = null) {
  const div = document.createElement('div');
  div.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;

  const avatar = document.createElement('span');
  avatar.className = 'msg-avatar';
  avatar.textContent = role === 'user' ? '🧑' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = text;

  if (emotion && role === 'user') {
    const em = document.createElement('div');
    em.className = 'msg-emotion';
    em.textContent = `${getEmoji(emotion)} ${emotion}`;
    bubble.appendChild(em);
  }

  div.appendChild(avatar);
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  scrollToBottom();
  return div;
}

function showTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'message assistant-message';
  div.id = 'typingIndicator';
  div.innerHTML = `<span class="msg-avatar">🤖</span>
    <div class="msg-bubble typing-dots"><span></span><span></span><span></span></div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ── Webcam ──
async function startCamera() {
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    webcamVideo.srcObject = webcamStream;
    btnStartCam.disabled = true;
    btnStopCam.disabled = false;
    setStatus(statusVision, true, '👁 Vision: on');
    startEmotionPolling();
  } catch (err) {
    console.error('Camera error:', err);
    appendMessage('assistant', '⚠️ Could not access camera. Please check permissions.');
  }
}

function stopCamera() {
  if (webcamStream) {
    webcamStream.getTracks().forEach(t => t.stop());
    webcamStream = null;
    webcamVideo.srcObject = null;
  }
  stopEmotionPolling();
  btnStartCam.disabled = false;
  btnStopCam.disabled = true;
  setStatus(statusVision, false, '👁 Vision: off');
}

// ── Emotion detection ──
function captureFrame() {
  const w = webcamVideo.videoWidth;
  const h = webcamVideo.videoHeight;
  if (!w || !h) return null;

  webcamCanvas.width  = w;
  webcamCanvas.height = h;
  const ctx = webcamCanvas.getContext('2d');
  // Mirror to match display
  ctx.translate(w, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(webcamVideo, 0, 0, w, h);
  // Return base64 without the data-URL prefix
  return webcamCanvas.toDataURL('image/jpeg', 0.6).split(',')[1];
}

async function detectEmotion() {
  const imageB64 = captureFrame();
  if (!imageB64) return;

  try {
    const resp = await fetch(`${API.vision}/detect-emotion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64: imageB64 }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    currentEmotion = data.emotion || 'neutral';
    updateEmotionUI(currentEmotion, data.confidence || 0);
  } catch (_) {
    // Vision service may not be reachable; silently ignore
  }
}

function updateEmotionUI(emotion, confidence) {
  emotionLabel.textContent = `${getEmoji(emotion)} ${emotion}`;
  emotionFill.style.width  = `${Math.round(confidence * 100)}%`;
}

function startEmotionPolling() {
  if (emotionInterval) return;
  emotionInterval = setInterval(detectEmotion, 3000); // every 3 s
}

function stopEmotionPolling() {
  clearInterval(emotionInterval);
  emotionInterval = null;
}

// ── Chat ──
async function sendMessage(text) {
  if (!text.trim()) return;
  userInput.value = '';

  appendMessage('user', text, currentEmotion);
  setStatus(statusAgent, false, '🧠 Agent: thinking…');
  showTypingIndicator();

  try {
    const resp = await fetch(`${API.agent}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, text, emotion: currentEmotion }),
    });

    if (!resp.ok) throw new Error(`Agent error: ${resp.status}`);
    const data = await resp.json();

    removeTypingIndicator();
    appendMessage('assistant', data.response);
    setStatus(statusAgent, true, '🧠 Agent: ready');

    // Speak the response
    await speakText(data.response);
  } catch (err) {
    removeTypingIndicator();
    appendMessage('assistant', `⚠️ Error: ${err.message}`);
    setStatus(statusAgent, false, '🧠 Agent: error');
  }
}

// ── TTS ──
async function speakText(text) {
  try {
    const resp = await fetch(`${API.tts}/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    audioPlayer.src = url;
    await audioPlayer.play().catch(() => {});
  } catch (_) {
    // TTS not critical; skip silently
  }
}

// ── Voice recording ──
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      stream.getTracks().forEach(t => t.stop());
      await transcribeAudio(blob);
    };
    mediaRecorder.start();
    isRecording = true;
    btnRecord.classList.add('recording');
    recordingIndicator.style.display = 'block';
    setStatus(statusSpeech, true, '🎙 Speech: recording');
  } catch (err) {
    console.error('Mic error:', err);
    appendMessage('assistant', '⚠️ Microphone access denied.');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;
  btnRecord.classList.remove('recording');
  recordingIndicator.style.display = 'none';
  setStatus(statusSpeech, false, '🎙 Speech: ready');
}

async function transcribeAudio(blob) {
  setStatus(statusSpeech, false, '🎙 Speech: transcribing…');
  try {
    const formData = new FormData();
    formData.append('audio', blob, 'recording.webm');

    const resp = await fetch(`${API.speech}/transcribe`, {
      method: 'POST',
      body: formData,
    });

    if (!resp.ok) throw new Error(`Speech error: ${resp.status}`);
    const data = await resp.json();

    if (data.text) {
      userInput.value = data.text;
      await sendMessage(data.text);
    } else {
      appendMessage('assistant', "🎙 I couldn't understand the audio. Please try again.");
    }
    setStatus(statusSpeech, true, '🎙 Speech: ready');
  } catch (err) {
    appendMessage('assistant', `⚠️ Transcription error: ${err.message}`);
    setStatus(statusSpeech, false, '🎙 Speech: error');
  }
}

// ── Profile / Memory ──
async function loadProfile() {
  try {
    const resp = await fetch(`${API.agent}/profile/${userId}`);
    if (!resp.ok) return;
    const profile = await resp.json();
    if (profile.name) userName.value = profile.name;
  } catch (_) {}
}

async function saveProfile() {
  const name = userName.value.trim();
  if (!name) return;
  try {
    await fetch(`${API.agent}/profile/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    appendMessage('assistant', `Nice to meet you, ${name}! I'll remember your name. 😊`);
  } catch (_) {}
}

async function loadEmotionHistory() {
  try {
    const resp = await fetch(`${API.agent}/memory/${userId}?limit=5`);
    if (!resp.ok) return;
    const data = await resp.json();
    emotionHistoryEl.innerHTML = '';
    data.history
      .filter(e => e.emotion)
      .slice(-5)
      .forEach(e => {
        const li = document.createElement('li');
        li.textContent = `${getEmoji(e.emotion)} ${e.emotion} – ${new Date(e.timestamp).toLocaleTimeString()}`;
        emotionHistoryEl.appendChild(li);
      });
  } catch (_) {}
}

// ── Event listeners ──
btnStartCam.addEventListener('click', startCamera);
btnStopCam.addEventListener('click', stopCamera);

btnSend.addEventListener('click', () => sendMessage(userInput.value));

userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(userInput.value);
  }
});

btnRecord.addEventListener('click', () => {
  if (isRecording) stopRecording();
  else startRecording();
});

sidebarToggle.addEventListener('click', () => {
  const visible = sidebarContent.style.display !== 'none';
  sidebarContent.style.display = visible ? 'none' : 'block';
  if (!visible) {
    loadEmotionHistory();
    loadProfile();
  }
});

btnSaveName.addEventListener('click', saveProfile);

// ── Init ──
loadProfile();
