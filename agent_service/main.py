"""
Agent Service – LLM-based conversational agent with emotional awareness and memory.

Endpoints:
  POST /chat         – Accept user text + emotion, return empathetic AI response.
  GET  /memory/{uid} – Retrieve conversation history for a user.
  POST /memory/save  – Manually persist a memory entry.
  GET  /profile/{uid}– Get user profile.
  PUT  /profile/{uid}– Update user profile.
  GET  /health       – Health check.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory import (
    get_emotion_patterns,
    get_memory,
    get_user_profile,
    save_memory,
    update_user_profile,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Emotion → tone guidance mapping
EMOTION_TONE_MAP: Dict[str, str] = {
    "happy": "Be enthusiastic, warm, and match the user's positive energy.",
    "sad": "Be gentle, empathetic, and compassionate. Offer comfort and support.",
    "angry": "Be calm, patient, and de-escalating. Acknowledge their frustration.",
    "fear": "Be reassuring, steady, and supportive. Help them feel safe.",
    "surprise": "Be engaged, curious, and playful.",
    "disgust": "Be understanding, validating, and calm.",
    "neutral": "Be friendly, conversational, and helpful.",
    "contempt": "Be respectful, empathetic, and non-confrontational.",
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str = "default"
    text: str
    emotion: Optional[str] = "neutral"


class ChatResponse(BaseModel):
    response: str
    emotion_detected: str
    user_id: str


class MemorySaveRequest(BaseModel):
    user_id: str
    role: str
    content: str
    emotion: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helper: build system prompt
# ---------------------------------------------------------------------------

def _build_system_prompt(user_id: str, emotion: str) -> str:
    tone = EMOTION_TONE_MAP.get(emotion, EMOTION_TONE_MAP["neutral"])
    profile = get_user_profile(user_id)
    name_hint = f" The user's name is {profile['name']}." if profile.get("name") else ""
    emotion_history = get_emotion_patterns(user_id, limit=5)
    recent_emotions = ", ".join(e["emotion"] for e in emotion_history) if emotion_history else "none"

    return (
        "You are Jarvis, a warm and emotionally intelligent AI companion. "
        "You speak naturally, like a caring human friend.\n\n"
        f"Current detected emotion: {emotion}.\n"
        f"Tone guidance: {tone}\n"
        f"Recent emotional history: {recent_emotions}.\n"
        f"{name_hint}\n\n"
        "Keep responses concise (2-4 sentences) unless asked for detail. "
        "Never break character. Always acknowledge the emotional context."
    )


# ---------------------------------------------------------------------------
# Helper: call Ollama LLM
# ---------------------------------------------------------------------------

async def _call_ollama(messages: List[Dict[str, str]]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"].strip()
    except httpx.HTTPStatusError as exc:
        logger.error("Ollama HTTP error: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    except httpx.RequestError as exc:
        logger.error("Ollama connection error: %s", exc)
        # Fallback response when Ollama is not available
        return _fallback_response(messages[-1]["content"] if messages else "", "neutral")


def _fallback_response(user_text: str, emotion: str) -> str:
    """Simple rule-based fallback when LLM is unavailable."""
    tone = EMOTION_TONE_MAP.get(emotion, EMOTION_TONE_MAP["neutral"])
    responses = {
        "sad": "I hear you, and I'm here for you. Sometimes just talking about it helps.",
        "angry": "I understand you're frustrated. Take a breath — we'll work through this together.",
        "happy": "That's wonderful! Your positive energy is contagious!",
        "fear": "It's okay to feel scared. You're safe here, and I'm with you.",
        "neutral": f"Got it! You said: \"{user_text[:80]}\". How can I help you further?",
    }
    return responses.get(emotion, responses["neutral"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "agent_service"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Generate an emotionally-aware LLM response for the user's message.
    """
    user_id = request.user_id
    user_text = request.text.strip()
    emotion = (request.emotion or "neutral").lower()

    if not user_text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    # Retrieve recent conversation history
    history = get_memory(user_id, limit=10)

    # Build message list for Ollama
    system_prompt = _build_system_prompt(user_id, emotion)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})

    messages.append({"role": "user", "content": user_text})

    # Call LLM
    assistant_reply = await _call_ollama(messages)

    # Persist both turns
    save_memory(user_id, "user", user_text, emotion)
    save_memory(user_id, "assistant", assistant_reply, None)

    return ChatResponse(
        response=assistant_reply,
        emotion_detected=emotion,
        user_id=user_id,
    )


@app.get("/memory/{user_id}")
def read_memory(user_id: str, limit: int = 20):
    return {"user_id": user_id, "history": get_memory(user_id, limit)}


@app.post("/memory/save")
def write_memory(request: MemorySaveRequest):
    save_memory(request.user_id, request.role, request.content, request.emotion)
    return {"status": "saved"}


@app.get("/profile/{user_id}")
def read_profile(user_id: str):
    return get_user_profile(user_id)


@app.put("/profile/{user_id}")
def write_profile(user_id: str, request: ProfileUpdateRequest):
    update_user_profile(user_id, name=request.name, preferences=request.preferences)
    return {"status": "updated"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8003))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
