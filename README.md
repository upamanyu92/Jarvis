# 🤖 Jarvis – Emotion-Aware AI Companion

A local, privacy-first AI companion that **sees you** through the webcam, **listens** via microphone, **detects your emotions**, and responds in a natural human-like voice — all running fully on your machine.

---

## 🎯 Features

| Capability | Technology |
|---|---|
| Real-time webcam feed | Browser MediaDevices API |
| Face + emotion detection | DeepFace (OpenCV backend) |
| Speech-to-text | OpenAI Whisper |
| LLM conversation | Ollama (llama3 by default) |
| Emotion-aware responses | Custom prompt engineering |
| Conversation memory | SQLite via SQLAlchemy |
| Text-to-speech | gTTS |
| Frontend UI | HTML + vanilla JS |
| Orchestration | Docker Compose + Nginx |

---

## 🏗️ Architecture

```
Browser (frontend)
    │
    ├── /api/vision  ──▶ vision_service  (port 8001) – DeepFace emotion detection
    ├── /api/speech  ──▶ speech_service  (port 8002) – Whisper transcription
    ├── /api/agent   ──▶ agent_service   (port 8003) – LLM + memory
    └── /api/tts     ──▶ tts_service     (port 8004) – gTTS synthesis
                              │
                              └── ollama (port 11434) – local LLM
```

All services communicate via REST APIs through an Nginx reverse proxy.

---

## 📦 Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20
- A webcam and microphone (accessed by the browser)
- ~8 GB RAM (for llama3 model; use `tinyllama` for lower memory)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/upamanyu92/Jarvis.git
cd Jarvis
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if you want a different Whisper model or LLM
```

### 3. Start all services

```bash
docker compose up --build
```

This will:
- Build all four Python microservices
- Pull the Ollama image
- Start Nginx on port **80**

### 4. Pull the LLM model

In a **separate terminal**, once Ollama is running:

```bash
docker exec jarvis_ollama ollama pull llama3
```

> **Tip:** For faster startup on low-RAM machines, use `tinyllama` instead:
> ```bash
> docker exec jarvis_ollama ollama pull tinyllama
> # Set OLLAMA_MODEL=tinyllama in .env, then restart
> ```

### 5. Open the UI

Navigate to **http://localhost** in your browser.

---

## 🧩 Services

### vision_service  (`:8001`)
- `POST /detect-emotion` – accepts a base64-encoded JPEG, returns `{ emotion, confidence, all_emotions }`
- `GET  /health`

### speech_service  (`:8002`)
- `POST /transcribe` – accepts multipart audio upload, returns `{ text, language }`
- `GET  /health`

### agent_service   (`:8003`)
- `POST /chat`             – `{ user_id, text, emotion }` → `{ response, emotion_detected, user_id }`
- `GET  /memory/{user_id}` – conversation history
- `POST /memory/save`      – manually save a memory entry
- `GET  /profile/{user_id}`– user profile
- `PUT  /profile/{user_id}`– update name / preferences
- `GET  /health`

### tts_service     (`:8004`)
- `POST /synthesize` – `{ text, language?, slow? }` → MP3 audio stream
- `GET  /health`

---

## 💡 Usage

1. Click **▶ Start Camera** – the webcam starts and emotion detection polls every 3 seconds.
2. **Type** a message in the input box and press **Enter** or click **Send**.
3. Click the 🎙 **mic button** to record voice; click again to stop and auto-transcribe.
4. Jarvis responds in text and speaks the reply aloud.
5. Click ☰ **Profile** in the top-right to set your name and view emotion history.

---

## 🔄 Data Flow

```
Webcam frame  ──▶  vision_service  ──▶  emotion (e.g. "sad")
                                                │
Mic audio     ──▶  speech_service  ──▶  text    │
                                          │      │
                                    agent_service (LLM + memory)
                                          │
                                   response text
                                          │
                                    tts_service  ──▶  MP3 audio
```

---

## 🧪 Running Tests

Install test dependencies (once):

```bash
pip install fastapi httpx sqlalchemy pytest pytest-asyncio \
            openai-whisper gtts opencv-python-headless deepface \
            tf-keras numpy
```

Run all tests:

```bash
cd tests
pytest -v
```

Run a specific suite:

```bash
pytest tests/test_agent.py -v
pytest tests/test_tts.py   -v
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | LLM model name |
| `TTS_LANGUAGE` | `en` | gTTS language code |
| `DATABASE_URL` | `sqlite:////data/jarvis_memory.db` | SQLAlchemy DB URL |

---

## 🗂️ Project Structure

```
Jarvis/
├── vision_service/      # DeepFace emotion detection
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── speech_service/      # Whisper speech-to-text
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── agent_service/       # Ollama LLM + memory
│   ├── main.py
│   ├── memory.py
│   ├── requirements.txt
│   └── Dockerfile
├── tts_service/         # gTTS text-to-speech
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # HTML/JS UI
│   ├── index.html
│   ├── app.js
│   └── style.css
├── nginx/
│   └── nginx.conf       # Reverse proxy config
├── tests/               # Pytest test suites
│   ├── test_vision.py
│   ├── test_speech.py
│   ├── test_agent.py
│   ├── test_tts.py
│   └── test_pipeline.py
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔒 Privacy

All processing runs **locally** on your machine. No audio, video, or conversation data is sent to external servers.

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss any major changes.

---

## 📄 License

[MIT](LICENSE)
